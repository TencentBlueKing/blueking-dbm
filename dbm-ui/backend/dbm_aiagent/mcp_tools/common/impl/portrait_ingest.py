# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像 MCP - 写侧业务实现（供 View 调用）。

模块职责：
    - 面向 MCP 视图层，负责：
        1) 通过 (bk_biz_id, cluster_domain) **反查集群对象**（复用
           :meth:`PortraitQueryService.resolve_cluster`），从 ``cluster.cluster_type``
           归一化得到 ``db_type``；从而免去调用方显式传 ``db_type`` 的负担，
           也避免调用方与集群元数据口径不一致；本层还负责在 SDK 之前提供"友好的
           cluster_not_found 短路"，避免 Agent 拿到通用 invalid_payload 才反应过来；
        2) 把字符串 ``code`` 契约映射回 SDK 需要的强类型枚举成员；
        3) 调用 :func:`backend.db_report.portrait.ingest_summary` 完成落库；**集群语义
           校验（含 report_time 是否 >= cluster.create_at）已下沉为 SDK 唯一事实源**，
           适配层只做异常到 status 的翻译。
    - 把 SDK 抛出的可预期业务异常翻译为 MCP 出参约定的 ``status`` 字段
      （``ok`` / ``cluster_not_found`` / ``report_time_before_cluster_created`` /
      ``unsupported_db_type`` / ``invalid_code`` / ``invalid_payload``），
      不把内部异常直接暴露给前端 / Agent

设计要点：
    - 用类 :class:`PortraitIngestService` 组织；方法为 classmethod，无实例状态
    - **不做资源鉴权**：鉴权由视图层的 ``McpClusterDetailPermission`` + ``auth_parse_clusters`` 完成
    - **不改动写入语义**：真正的写入仍走 SDK 唯一入口；本层只是 MCP 通道的适配层
    - **异常翻译顺序敏感**：``except`` 子句必须按"子类在前 / 父类在后"排列，
      否则 :class:`PortraitReportTimeStaleException` 会先被父类
      :class:`PortraitInvalidPayloadException` 兜住，丢失细分 status 语义

边界：
    - (bk_biz_id, cluster_domain) 找不到集群              -> status="cluster_not_found"
    - SDK 抛 report_time 早于 create_at 异常              -> status="report_time_before_cluster_created"
    - 集群 db_type 未在维度枚举映射中登记（如新引擎未接入）-> status="unsupported_db_type"
    - code 在指定 db_type 下无对应枚举成员                 -> status="invalid_code"
    - 其它入参不合法（超长 / 类型错等）                    -> status="invalid_payload"
    - ORM 底层写失败（连接异常等不可预期）                 -> 不吞异常，向上抛出，由框架统一 500 处理
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, Type

from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_report.portrait import MysqlPortraitDimensionCode, RedisPortraitDimensionCode, ingest_summary
from backend.db_report.portrait.exceptions import PortraitInvalidPayloadException, PortraitReportTimeStaleException
from backend.dbm_aiagent.mcp_tools.common.impl.portrait_query import PortraitQueryService
from blue_krill.data_types.enum import StrStructuredEnum

logger = logging.getLogger("root")

#: db_type value（DBType.value，小写字符串） -> 该 DB 对应的维度枚举类
#: 说明：
#:   - 每新增一种 DB 的画像契约，只需在此映射中追加一行；
#:   - key 使用 DBType 的 value（如 "mysql" / "redis"）以对齐集群元数据 db_type 与 DB 表存储；
#:   - value 是 *PortraitDimensionCode 枚举类本身（Type[StrStructuredEnum]），
#:     视图侧只需要传字符串 code，本层通过 ``EnumCls(code_value)`` 反查具体成员。
_DB_TYPE_TO_DIMENSION_ENUM: Dict[str, Type[StrStructuredEnum]] = {
    DBType.MySQL.value: MysqlPortraitDimensionCode,
    DBType.TenDBCluster.value: MysqlPortraitDimensionCode,
    DBType.Redis.value: RedisPortraitDimensionCode,
}


class PortraitIngestService:
    """集群画像写侧适配服务。

    职责：
        - 面向 MCP View 层的单一方法 :meth:`ingest_summary`：
          反查集群 db_type -> 字符串 code -> 枚举 -> SDK
        - 归一化可预期失败为 status 字段（对齐 MCP 出参约定）
        - **集群语义校验（含 report_time 与 create_at 的对比）不在本层完成**，
          而是由 SDK :meth:`PortraitIngestSDK._validate_payload` 作为唯一事实源承担；
          本层仅通过 ``except`` 把 SDK 异常翻译为 status

    典型使用（View 层直接调 classmethod）::

        result = PortraitIngestService.ingest_summary(
            code="slow_query",
            bk_biz_id=100001,
            cluster_domain="a.b.c",
            report_time=datetime.now(),
            summary="...",
            detail_url="...",
        )

    线程安全：是（无实例状态）
    边界：见模块 docstring
    """

    @classmethod
    def ingest_summary(
        cls,
        code: str,
        bk_biz_id: Any,
        cluster_domain: str,
        report_time: Any,
        summary: Any = "",
        detail_url: Any = "",
        score: Any = None,
    ) -> Dict:
        """写入一条集群维度巡检摘要（MCP 写侧唯一入口）。

        执行流程：
            1) **入参规范化**：MCP/Agent 通道只能传 JSON 原生类型，本层负责把字符串 /
               数值形式的 ``report_time`` / ``bk_biz_id`` 等转换为 SDK 期望的强类型；
               规范化在最前是因为后续反查 db_type 依赖 ``bk_biz_id`` 为 int、
               ``cluster_domain`` 为非空 str
            2) **反查集群**：通过 :meth:`PortraitQueryService.resolve_cluster` 拿到集群对象；
               找不到 -> status="cluster_not_found"。这是**友好性短路**：SDK 侧同样会兜底
               校验集群存在性，但在这里前置返回，可以让 Agent 立即拿到明确的 status，
               而不必依赖异常翻译
            3) 从 ``cluster.cluster_type`` 归一化得到 db_type
            4) 通过 ``_DB_TYPE_TO_DIMENSION_ENUM`` 找到该 db_type 对应的维度枚举类；
               未登记 -> status="unsupported_db_type"
            5) 由 ``EnumCls(code)`` 得到具体维度成员；失败 -> status="invalid_code"
            6) 调 SDK :func:`ingest_summary` 完成"最后一道防线"校验 + 懒注册 + 写入；
               SDK 会在此处校验 ``report_time >= cluster.create_at``
            7) 异常翻译（顺序敏感，子类在前）：
               - :class:`PortraitReportTimeStaleException`
                 -> status="report_time_before_cluster_created"
               - :class:`PortraitInvalidPayloadException`（父类兜底）
                 -> status="invalid_payload"

        :param code: 该集群 db_type 下 ``*PortraitDimensionCode`` 枚举的 value（如 ``"slow_query"``）；
                     对应 MCP 入参 ``dimension_code``，由 View 层从 ``dimension_code`` 取值后传入
        :param bk_biz_id: 业务 ID；接受 ``int`` 或纯数字字符串（如 ``"100001"``），最终必须 > 0
        :param cluster_domain: 集群不可变主域名；将用于反查 db_type
        :param report_time: 本次巡检业务时间；接受以下三种形式：
                            - :class:`datetime.datetime` 对象（原样使用）
                            - ISO 8601 字符串（如 ``"2026-07-28T17:00:00+08:00"``、``"2026-07-28 17:00:00"``、
                              以 ``Z`` 结尾的 UTC 表示等；由 :meth:`_parse_report_time` 解析）
                            - int / float：视为 UNIX 时间戳（秒），自动转 :class:`datetime`
                            **必须 >= 目标集群 ``create_at``**，否则会被 SDK 拒绝
        :param summary: 摘要文本，允许为空；<= 4000 字符
        :param detail_url: 详情页链接，允许为空；<= 1024 字符
        :param score: 摘要结果分数；允许为 None（表示未上报）；数值 int/float（排除 bool）-> float
        :return: dict，字段结构对齐 ``PortraitIngestSummaryOutputSerializer``::

            {
              "status": "ok" | "cluster_not_found" | "report_time_before_cluster_created"
                        | "unsupported_db_type" | "invalid_code" | "invalid_payload",
              "id": int,                # 仅 status=ok 时 >0
              "db_type": str,           # 服务端反查得到；失败分支可能为空
              "dimension_code": str,    # 回显（对应入参 dimension_code）
              "message": str,           # 失败分支的可读原因
            }

        边界 / 异常：
            - 可预期分支均通过 status 表达，不向上抛异常
            - ORM 写失败等不可预期异常仍向上抛出，由框架 500 兜底

        注意：
            出参 dict 中**不使用** ``code`` 作为键名，改用 ``dimension_code``。
            原因是外层 ``BKAPIRenderer`` 对返回体做统一封装时，若 dict 中含有顶层 ``code``
            键会走"用户已自定义标准返回"短路分支，直接把业务 dict 作为响应体输出，
            造成 Go MCP 网关 unmarshal ``code``(int) 失败。
        """
        # 1) 入参规范化：把 MCP/Agent 通道的字符串/数值类型正规化为 SDK 要求的强类型
        #    放在最前是因为后续反查 db_type 需要 bk_biz_id 为 int、cluster_domain 为非空 str
        normalized, err_msg = cls._normalize_payload(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            report_time=report_time,
            summary=summary,
            detail_url=detail_url,
            score=score,
        )
        if err_msg is not None:
            return cls._fail(
                status="invalid_payload",
                db_type="",
                code=code,
                message=err_msg,
            )

        norm_biz_id: int = normalized["bk_biz_id"]
        norm_cluster_domain: str = normalized["cluster_domain"]
        norm_report_time: datetime = normalized["report_time"]

        # 2) 反查集群对象：由 (bk_biz_id, cluster_domain) -> Cluster
        #    这是"友好性短路"：SDK 侧也会兜底校验集群存在性，但前置返回可以让 Agent
        #    立即拿到明确的 cluster_not_found，而不是通过 invalid_payload 反查原因
        cluster = PortraitQueryService.resolve_cluster(bk_biz_id=norm_biz_id, cluster_domain=norm_cluster_domain)
        if cluster is None:
            return cls._fail(
                status="cluster_not_found",
                db_type="",
                code=code,
                message=str(_("集群未找到或不属于该业务：bk_biz_id={biz}, cluster_domain={cluster}")).format(
                    biz=norm_biz_id, cluster=norm_cluster_domain
                ),
            )

        # 3) 从 cluster.cluster_type 归一化得到 db_type
        db_type_str: str = ClusterType.cluster_type_to_db_type(cluster.cluster_type)

        # 4) 反查得到的字符串再映射为 DBType 枚举成员；理论一定命中，此处仅为兜底
        db_type_enum: Optional[DBType] = cls._parse_db_type(db_type_str)
        if db_type_enum is None:
            return cls._fail(
                status="unsupported_db_type",
                db_type=db_type_str,
                code=code,
                message=str(_("集群反查得到的 db_type={db_type} 非 DBType 枚举成员")).format(db_type=db_type_str),
            )

        # 5) db_type -> 维度枚举类；未登记则视为"暂未接入画像"
        dimension_enum_cls: Optional[Type[StrStructuredEnum]] = _DB_TYPE_TO_DIMENSION_ENUM.get(db_type_enum.value)
        if dimension_enum_cls is None:
            return cls._fail(
                status="unsupported_db_type",
                db_type=db_type_enum.value,
                code=code,
                message=str(_("db_type={db_type} 尚未接入画像维度枚举；已接入的 db_type：{allowed}")).format(
                    db_type=db_type_enum.value, allowed=sorted(_DB_TYPE_TO_DIMENSION_ENUM.keys())
                ),
            )

        # 6) 字符串 code -> 具体维度枚举成员（各 DB 命名空间隔离）
        try:
            dimension_member: StrStructuredEnum = dimension_enum_cls(code)
        except ValueError:
            allowed_codes = [str(member.value) for member in dimension_enum_cls]
            return cls._fail(
                status="invalid_code",
                db_type=db_type_enum.value,
                code=code,
                message=str(_("dimension_code 在 db_type={db_type} 下未定义；允许的取值：{allowed}")).format(
                    db_type=db_type_enum.value, allowed=allowed_codes
                ),
            )

        # 7) 委托 SDK 完成"最后一道防线"校验 + 懒注册 + 落库
        #    集群语义校验（含 report_time >= cluster.create_at）在这里被 SDK 强制执行
        try:
            record = ingest_summary(
                db_type=db_type_enum,
                dimension=dimension_member,
                bk_biz_id=norm_biz_id,
                cluster_domain=norm_cluster_domain,
                report_time=norm_report_time,
                summary=normalized["summary"],
                detail_url=normalized["detail_url"],
                score=normalized["score"],
            )
        except PortraitReportTimeStaleException as exc:
            # 8a) SDK 侧"report_time 早于集群创建时间"专用异常 -> 独立 status 分支
            #     注意：此 except 必须在 PortraitInvalidPayloadException 之前，
            #     否则会被父类兜住，丢失细分语义
            reason: str = cls._extract_exc_message(exc)
            logger.warning(
                "[portrait_ingest] report_time before cluster created: "
                "db_type=%s code=%s biz=%s cluster=%s reason=%s",
                db_type_enum.value,
                code,
                norm_biz_id,
                norm_cluster_domain,
                reason,
            )
            return cls._fail(
                status="report_time_before_cluster_created",
                db_type=db_type_enum.value,
                code=code,
                message=reason or str(_("report_time 早于集群创建时间")),
            )
        except PortraitInvalidPayloadException as exc:
            # 8b) SDK 侧其它可预期业务异常（含 PortraitClusterNotFoundException 兜底分支等）
            #     -> 归一化为 invalid_payload
            reason = cls._extract_exc_message(exc)
            logger.warning(
                "[portrait_ingest] invalid payload: db_type=%s code=%s biz=%s cluster=%s reason=%s",
                db_type_enum.value,
                code,
                norm_biz_id,
                norm_cluster_domain,
                reason,
            )
            return cls._fail(
                status="invalid_payload",
                db_type=db_type_enum.value,
                code=code,
                message=reason or str(_("入参不合法")),
            )

        return {
            "status": "ok",
            "id": int(record.id),
            "db_type": db_type_enum.value,
            "dimension_code": str(dimension_member.value),
            "message": "",
        }

    # ------------------------------------------------------------------
    # 私有辅助
    # ------------------------------------------------------------------

    @classmethod
    def _parse_db_type(cls, db_type: str) -> Optional[DBType]:
        """把字符串 ``db_type`` 解析为 :class:`DBType` 成员；不匹配返回 None。"""
        if not db_type or not isinstance(db_type, str):
            return None
        try:
            return DBType(db_type)
        except ValueError:
            return None

    @classmethod
    def _normalize_payload(
        cls,
        bk_biz_id: Any,
        cluster_domain: Any,
        report_time: Any,
        summary: Any,
        detail_url: Any,
        score: Any = None,
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """把 MCP/Agent 通道的宽松入参正规化为 SDK 期望的强类型。

        规则：
            - ``bk_biz_id``：int / 纯数字 str -> int；其它 -> 报错
            - ``cluster_domain``：非空 str -> 原样；其它 -> 报错（SDK 亦会再校一次）
            - ``report_time``：``datetime`` / ISO8601 str / 数值时间戳 -> ``datetime``；
              其它 -> 报错
            - ``summary`` / ``detail_url``：None -> ""；非 str 也 None -> ""（SDK 再做长度校验）
            - ``score``：None -> None；数值 int/float（排除 bool）-> float；其它 -> None（SDK 再校验）

        :param bk_biz_id: 业务 ID 原始值（可能为 int 或 str）
        :param cluster_domain: 集群域名原始值
        :param report_time: 巡检时间原始值（可能为 datetime / str / 数值）
        :param summary: 摘要文本原始值
        :param detail_url: 详情链接原始值
        :param score: 摘要分数原始值（可能为 int / float / None）
        :return: (规范化后的字典, 错误消息)。错误消息为 None 表示成功；
                 否则调用方应把该消息透传到 status="invalid_payload" 分支。
        边界：本方法**只做类型转换 + 明显非法**兜底，具体格式类校验（长度、正整数等）
             仍交给 SDK ``_validate_payload``，保持"唯一事实源"。
        """
        # bk_biz_id：允许 int 或纯数字字符串
        biz_id_val: Optional[int] = cls._coerce_int(bk_biz_id)
        if biz_id_val is None:
            return {}, str(_("bk_biz_id 必须为正整数或纯数字字符串，收到：{value!r}")).format(value=bk_biz_id)

        # cluster_domain：仅做非空 + 类型兜底；长度 / 语义交给 SDK 与上层 permission
        if not isinstance(cluster_domain, str) or not cluster_domain:
            return {}, str(_("cluster_domain 必须为非空字符串，收到：{value!r}")).format(value=cluster_domain)

        # report_time：datetime / ISO8601 str / 时间戳数值 -> datetime
        rt_val: Optional[datetime] = cls._parse_report_time(report_time)
        if rt_val is None:
            return {}, str(
                _(
                    "report_time 无法解析为 datetime；请传 datetime 对象、ISO8601 字符串"
                    "（如 '2026-07-28T17:00:00+08:00'）或 UNIX 时间戳（秒）。收到：{value!r}"
                )
            ).format(value=report_time)

        # summary / detail_url：None 兜底为空串；SDK 会再做长度校验
        summary_val: str = summary if isinstance(summary, str) else ("" if summary is None else str(summary))
        detail_val: str = (
            detail_url if isinstance(detail_url, str) else ("" if detail_url is None else str(detail_url))
        )

        # score：None -> None；数值 int/float（排除 bool）-> float；其它 -> None（SDK 再做校验）
        score_val: Optional[float] = cls._coerce_score(score)

        return (
            {
                "bk_biz_id": biz_id_val,
                "cluster_domain": cluster_domain,
                "report_time": rt_val,
                "summary": summary_val,
                "detail_url": detail_val,
                "score": score_val,
            },
            None,
        )

    @staticmethod
    def _coerce_int(value: Any) -> Optional[int]:
        """将 int / 纯数字字符串转换为 int；不合法返回 None。

        :param value: 原始值（可能为 int / str / 其它）
        :return: 合法的正整数或 None
        边界：布尔值虽然是 int 的子类，但语义上不应被视为业务 ID，视为非法
        """
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().lstrip("-").isdigit():
            try:
                return int(value.strip())
            except ValueError:
                return None
        return None

    @staticmethod
    def _coerce_score(value: Any) -> Optional[float]:
        """将宽松形式的分数入参转换为 float；不合法返回 None。

        :param value: 原始值（可能为 int / float / None / 其它）
        :return: 合法的 float 或 None
        边界：布尔值虽然是 int 的子类，但语义上不应被视为分数，视为非法（返回 None）
        """
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        return None

    @staticmethod
    def _parse_report_time(value: Any) -> Optional[datetime]:
        """把宽松形式的时间入参解析为 :class:`datetime`；不合法返回 None。

        支持形式：
            - :class:`datetime`：原样返回
            - :class:`str`：按 ISO 8601 解析；容忍以 ``Z`` 结尾的 UTC 表示
            - :class:`int` / :class:`float`：视为 UNIX 时间戳（秒），转换为**带 UTC 时区**的 datetime

        :param value: 原始时间入参
        :return: :class:`datetime` 或 None
        边界：本方法不做时区转换/兜底加时区，交给下游按业务约定处理；
             但 UNIX 时间戳分支为了避免语义歧义，会带上 UTC 时区
        """
        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            s = value.strip()
            if not s:
                return None
            # 容忍 '...Z' 结尾（Python 3.11 fromisoformat 已支持，但兼容更早行为）
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            try:
                return datetime.fromisoformat(s)
            except ValueError:
                return None

        # bool 是 int 的子类，需要显式排除，防止 True/False 被当成时间戳
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(float(value), tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                return None

        return None

    @staticmethod
    def _extract_exc_message(exc: BaseException) -> str:
        """尽量鲁棒地从异常实例里提取一条可读的原因。

        兼容三种常见承载方式：
            - ``exc.context = {"msg": "..."}``（本项目 :class:`AppBaseException` 惯例）
            - ``exc.message`` 属性
            - ``str(exc)`` 兜底

        :param exc: 任意异常实例
        :return: 可读的错误原因字符串；若都拿不到则返回空串
        """
        ctx = getattr(exc, "context", None)
        if isinstance(ctx, dict):
            msg = ctx.get("msg") or ctx.get("message")
            if msg:
                return str(msg)

        attr_msg = getattr(exc, "message", None)
        if attr_msg:
            return str(attr_msg)

        try:
            return str(exc)
        except Exception:  # pylint: disable=broad-except
            return ""

    @classmethod
    def _fail(cls, status: str, db_type: str, code: str, message: str) -> Dict:
        """构造统一失败出参，避免各分支重复。

        :param db_type: 反查得到的 db_type 字符串（可能为空串，如反查失败分支）
        :param code: 维度短码原始入参值（回显用），对外 dict 键名为 ``dimension_code``
        """
        return {
            "status": status,
            "id": 0,
            "db_type": db_type or "",
            "dimension_code": code or "",
            "message": message,
        }
