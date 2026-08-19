# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像 SDK 核心实现。

模块职责：
    - 面向各巡检维度开发者，提供**唯一稳定入口** :func:`ingest_summary`
    - 内部封装为类 :class:`PortraitIngestSDK`：校验 → 懒注册 → 落库 三段式流水线
    - 与 MCP 侧完全解耦：SDK 只写 :class:`PortraitDimensionSummary`，Agent 侧只读

设计要点：
    - ``db_type`` 显式使用 :class:`DBType` 枚举传入；契约来源清晰，类型系统兜住
    - ``dimension`` 使用各 DB 独立的 ``*PortraitDimensionCode`` 枚举（如 :class:`MysqlPortraitDimensionCode`），
      各 DB 命名空间**完全隔离**，即使 code 命名相同也互不干扰
    - 首次上报即自动懒注册到 :class:`PortraitDimensionRegistry`（无需运维执行 command）
    - 每次上报都用枚举里的当前 name / description 做 upsert 同步（枚举 = 事实源）
    - **集群语义校验作为唯一事实源**：``_validate_payload`` 反查 :class:`Cluster`，
      校验目标集群存在、且 ``report_time >= cluster.create_at``。所有写入路径
      （MCP / 定时任务 / 告警回调 / 运维脚本）都会经过这道"最后防线"，
      不依赖上层适配器额外校验，避免"上一代同域名集群"的脏数据入库
    - **时区归一化**：Django 默认 ``USE_TZ=True``，``Cluster.create_at`` 是 aware datetime；
      调用方传入的 ``report_time`` 可能是 naive（如脚本直接传 ``datetime.now()``）。
      SDK 内部用 :meth:`_to_aware` 归一化后再比较，避免 ``TypeError``
    - 所有失败路径统一抛出 :class:`PortraitInvalidPayloadException` 或其子类，不吞异常；
      具体子类见 :mod:`.exceptions`（``PortraitClusterNotFoundException`` /
      ``PortraitReportTimeStaleException``），上层可细分捕获

调用示例（供巡检开发者）::

    from datetime import datetime
    from backend.configuration.constants import DBType
    from backend.db_report.portrait import MysqlPortraitDimensionCode, ingest_summary

    ingest_summary(
        db_type=DBType.MySQL,
        dimension=MysqlPortraitDimensionCode.SLOW_QUERY,
        bk_biz_id=100001,
        cluster_domain="a.b.c.example.com",
        report_time=datetime.now(),
        summary="近 24h 慢日志同比 +32%，Top1 SQL 未走索引",
        detail_url="https://xxx"
    )
"""
import logging
from datetime import datetime
from typing import Optional

from django.utils import timezone as django_timezone
from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import DBType
from backend.db_meta.models import Cluster
from backend.db_report.models.portrait_dimension_summary import PortraitDimensionSummary
from backend.db_report.portrait.exceptions import (
    PortraitClusterNotFoundException,
    PortraitInvalidPayloadException,
    PortraitReportTimeStaleException,
)
from backend.db_report.portrait.registry_helper import RegistryHelper
from blue_krill.data_types.enum import StrStructuredEnum

logger = logging.getLogger("root")

#: summary 字段最大长度上限；单位：字符（非字节）。TextField 本身无长度限制，
#: 此常量用于 SDK 层软限制，防止调用方误传超大 blob 影响 LLM 上下文
_MAX_SUMMARY_CHARS: int = 4000

#: detail_url 字段长度上限；与 PortraitDimensionSummary.detail_url max_length 一致
_MAX_DETAIL_URL_CHARS: int = 1024


class PortraitIngestSDK:
    """集群画像摘要上报 SDK 主体。

    职责：
        - 面向巡检开发者的写入门面：校验 → 懒注册 → 追加写摘要
        - 通过 :meth:`ingest` 单一入口完成一次上报
        - **集群语义校验唯一事实源**：不再依赖上层适配器（MCP View / celery task / 脚本）
          自行做集群存在性与创建时间校验；所有写入都会在 :meth:`_validate_payload` 中
          反查 :class:`Cluster` 并对齐 ``create_at``

    典型使用（推荐通过模块级快捷函数 :func:`ingest_summary` 调用，见文件末尾）::

        PortraitIngestSDK().ingest(
            db_type=DBType.MySQL,
            dimension=MysqlPortraitDimensionCode.SLOW_QUERY,
            bk_biz_id=100001,
            cluster_domain="a.b.c",
            report_time=datetime.now(),
            summary="...", detail_url="...",
        )

    线程安全：是（无实例状态）
    边界：
        - db_type 不是 :class:`DBType` 成员                          -> :class:`PortraitInvalidPayloadException`
        - dimension 不是 :class:`StrStructuredEnum` 成员             -> :class:`PortraitInvalidPayloadException`
        - (bk_biz_id, cluster_domain) 反查不到集群                    -> :class:`PortraitClusterNotFoundException`
        - report_time < cluster.create_at                            -> :class:`PortraitReportTimeStaleException`
        - 已禁用维度（enabled=False）                                 -> **不阻塞上报**，正常写入；enabled 只影响读侧
        - 未注册维度                                                  -> **自动懒注册**，无异常抛出
        - 其它入参非法（空、超长、类型错）                            -> :class:`PortraitInvalidPayloadException`
        - 数据库写入异常                                              -> 由 Django ORM 抛原生异常，SDK 不吞掉
    """

    #: summary 字段最大长度（软限制），公开为类属性以便测试覆写
    MAX_SUMMARY_CHARS: int = _MAX_SUMMARY_CHARS

    #: detail_url 字段最大长度（与 Model max_length 对齐）
    MAX_DETAIL_URL_CHARS: int = _MAX_DETAIL_URL_CHARS

    def ingest(
        self,
        db_type: DBType,
        dimension: StrStructuredEnum,
        bk_biz_id: int,
        cluster_domain: str,
        report_time: datetime,
        summary: str = "",
        detail_url: str = "",
        score: Optional[float] = None,
    ) -> PortraitDimensionSummary:
        """写入一条巡检维度摘要。

        执行流程：
            1) 类型 / 格式 / **集群语义** 校验（:meth:`_validate_payload`）
            2) 从入参 + 枚举提取 (db_type_value, code, name, description)
            3) 注册表懒注册（:meth:`RegistryHelper.ensure_registered`）
            4) 追加写入 :class:`PortraitDimensionSummary` 表

        :param db_type: :class:`DBType` 枚举成员（如 ``DBType.MySQL``）；显式声明所属 DB
        :param dimension: 具体 DB 的 ``*PortraitDimensionCode`` 枚举成员（如 :class:`MysqlPortraitDimensionCode`）
        :param bk_biz_id: CMDB 业务 ID，必须 > 0
        :param cluster_domain: 集群不可变域名，非空；对应 :class:`Cluster` 的 ``immute_domain``
        :param report_time: 本次巡检的业务时间，datetime 类型（精确到秒即可）；
                            **必须 >= 目标集群 ``create_at``**，否则视为脏数据被拒绝
        :param summary: 本次巡检的摘要文本；允许为空字符串（视为无风险要点）；单条 <= 4000 字符
        :param detail_url: 本次巡检详情页链接；允许为空；<= 1024 字符
        :param score: 本次摘要结果的分数；允许为 None（表示未上报）；若传入须为数值（int/float，排除 bool）
        :return: 新落库的 :class:`PortraitDimensionSummary` 实例（含自增 id）

        边界 / 异常：
            - db_type / dimension 类型错 / 其它入参不合法 -> :class:`PortraitInvalidPayloadException`
            - 集群不存在                                   -> :class:`PortraitClusterNotFoundException`
            - report_time 早于集群创建时间                  -> :class:`PortraitReportTimeStaleException`
            - 维度未注册                                   -> 自动创建注册表记录，然后正常写入
            - 维度已禁用 (enabled=False)                    -> 不影响上报（enabled 只影响 Agent 读侧）
            - DB 写入失败                                  -> Django ORM 原生异常（不由 SDK 转换）
        """
        # 1) 参数校验（快速失败）：包含类型格式 + 集群语义校验
        self._validate_payload(
            db_type=db_type,
            dimension=dimension,
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            report_time=report_time,
            summary=summary,
            detail_url=detail_url,
            score=score,
        )

        # 2) 提取契约字段：db_type_value 落库用小写字符串；code/name/description 来自枚举
        db_type_value: str = str(db_type.value)
        code: str = str(dimension.value)
        name: str = str(type(dimension).get_choice_label(dimension.value))
        description: str = str(getattr(dimension, "description", ""))

        # 3) 懒注册 / 元数据同步；enabled 由此方法内部保持不变
        RegistryHelper.ensure_registered(
            db_type=db_type_value,
            code=code,
            name=name,
            description=description,
        )

        # 4) 追加写入摘要表（不做 upsert，语义上"每次巡检 = 一条记录"）
        record: PortraitDimensionSummary = PortraitDimensionSummary.objects.create(
            db_type=db_type_value,
            code=code,
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            report_time=report_time,
            summary=summary or "",
            detail_url=detail_url or "",
            score=score,
        )

        logger.info(
            "[portrait_sdk] ingested summary: db_type=%s code=%s biz=%s cluster=%s time=%s id=%s",
            db_type_value,
            code,
            bk_biz_id,
            cluster_domain,
            report_time,
            record.id,
        )
        return record

    # ------------------------------------------------------------------
    # 私有辅助
    # ------------------------------------------------------------------

    def _validate_payload(
        self,
        db_type: DBType,
        dimension: StrStructuredEnum,
        bk_biz_id: int,
        cluster_domain: str,
        report_time: datetime,
        summary: str,
        detail_url: str,
        score: Optional[float],
    ) -> None:
        """入参格式 + 集群语义校验；不合法直接抛出 :class:`PortraitInvalidPayloadException` 或其子类。

        校验分两层，均在 SDK 内完成，作为所有写入通道的**唯一权威防线**：

        A. 类型 / 格式校验（无 IO）：
            - db_type 必须是 :class:`DBType` 成员
            - dimension 必须是 :class:`StrStructuredEnum` 成员（由 IDE 编译期与本运行时兜底共同保证）
            - bk_biz_id / cluster_domain / report_time / summary / detail_url 的空、类型、长度

        B. 集群语义校验（一次 DB 查询）：
            - (bk_biz_id, cluster_domain) 必须能反查到 :class:`Cluster` 记录
              -> 否则抛 :class:`PortraitClusterNotFoundException`
            - ``report_time`` 必须 >= ``cluster.create_at``，防止"上一代同域名集群"脏数据入库
              -> 否则抛 :class:`PortraitReportTimeStaleException`
            - 时区归一化：naive datetime 用 :meth:`_to_aware` 补 tzinfo 后再比较

        校验策略：
            - 一条错误信息即抛出，不做累积（快速失败利于调用方定位）
            - 集群语义校验放在格式校验**之后**，保证 bk_biz_id / cluster_domain / report_time
              已是合法类型再访问 DB

        :raises PortraitInvalidPayloadException: 任一格式校验项不通过
        :raises PortraitClusterNotFoundException: 目标集群不存在（``PortraitInvalidPayloadException`` 子类）
        :raises PortraitReportTimeStaleException: report_time 早于集群创建时间
            （``PortraitInvalidPayloadException`` 子类）
        """
        # ---- A. 类型 / 格式校验 ------------------------------------------
        if not isinstance(db_type, DBType):
            raise PortraitInvalidPayloadException(context={"msg": _("db_type 必须是 DBType 枚举成员")})

        if not isinstance(dimension, StrStructuredEnum):
            raise PortraitInvalidPayloadException(context={"msg": _("dimension 必须是 *PortraitDimensionCode 枚举成员")})

        if not isinstance(bk_biz_id, int) or bk_biz_id <= 0:
            raise PortraitInvalidPayloadException(context={"msg": _("bk_biz_id 必须为正整数")})

        if not cluster_domain or not isinstance(cluster_domain, str):
            raise PortraitInvalidPayloadException(context={"msg": _("cluster_domain 必须为非空字符串")})

        if not isinstance(report_time, datetime):
            raise PortraitInvalidPayloadException(context={"msg": _("report_time 必须为 datetime 类型")})

        if summary is not None and not isinstance(summary, str):
            raise PortraitInvalidPayloadException(context={"msg": _("summary 必须为字符串")})

        if summary and len(summary) > self.MAX_SUMMARY_CHARS:
            raise PortraitInvalidPayloadException(
                context={"msg": _("summary 长度超过上限 {limit} 字符").format(limit=self.MAX_SUMMARY_CHARS)}
            )

        if detail_url is not None and not isinstance(detail_url, str):
            raise PortraitInvalidPayloadException(context={"msg": _("detail_url 必须为字符串")})

        if detail_url and len(detail_url) > self.MAX_DETAIL_URL_CHARS:
            raise PortraitInvalidPayloadException(
                context={"msg": _("detail_url 长度超过上限 {limit} 字符").format(limit=self.MAX_DETAIL_URL_CHARS)}
            )

        if score is not None:
            # score 允许 int/float，但排除 bool（bool 是 int 子类，语义上不应作为分数）
            if isinstance(score, bool) or not isinstance(score, (int, float)):
                raise PortraitInvalidPayloadException(context={"msg": _("score 必须为数值类型（int/float）或 None")})

        # ---- B. 集群语义校验 --------------------------------------------
        cluster_created_at: Optional[datetime] = self._get_cluster_created_at(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
        )
        if cluster_created_at is None:
            raise PortraitClusterNotFoundException(
                context={
                    "msg": _("集群未找到或不属于该业务：bk_biz_id={biz}, cluster_domain={cluster}").format(
                        biz=bk_biz_id, cluster=cluster_domain
                    )
                }
            )

        rt_aware: datetime = self._to_aware(report_time)
        created_aware: datetime = self._to_aware(cluster_created_at)
        if rt_aware < created_aware:
            raise PortraitReportTimeStaleException(
                context={
                    "msg": _(
                        "report_time={rt} 早于集群创建时间 cluster_created_at={created}；" "该数据可能属于上一代同域名集群，已从源头拦截以避免脏数据入库。"
                    ).format(rt=rt_aware.isoformat(), created=created_aware.isoformat())
                }
            )

    @staticmethod
    def _get_cluster_created_at(bk_biz_id: int, cluster_domain: str) -> Optional[datetime]:
        """反查 (bk_biz_id, cluster_domain) 对应集群的 ``create_at``；找不到返回 ``None``。

        设计要点 / 怎么做：
            - 数据源：:class:`Cluster` 表；按 ``bk_biz_id + immute_domain`` 唯一定位
            - 只 ``.values_list("create_at")`` 拿单字段，避免加载整个 ORM 对象；同时用
              ``.first()`` 而非 ``.get()`` 显式处理不存在分支，避免 ``DoesNotExist`` 异常
            - **不复用**上层 ``PortraitQueryService.resolve_cluster``：SDK 位于 ``db_report``
              下层，不能反向依赖 ``dbm_aiagent`` 上层 MCP 模块

        :param bk_biz_id: 业务 ID
        :param cluster_domain: 集群不可变主域名（``immute_domain``）
        :return: 集群创建时间 datetime；集群不存在时返回 ``None``
        边界 / 异常：
            - 集群不存在 -> ``None``（不抛异常，由调用方转成具体业务异常）
            - ORM 层不可预期异常 -> 原样抛出，由框架 500 兜底
        """
        return (
            Cluster.objects.filter(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
            .values_list("create_at", flat=True)
            .first()
        )

    @staticmethod
    def _to_aware(value: datetime) -> datetime:
        """把 naive datetime 标记为 Django 当前默认时区的 aware datetime；aware 原样返回。

        设计要点 / 怎么做：
            - Django 默认 ``USE_TZ=True``，ORM 读出的 datetime 是 aware（UTC）
            - 调用方可能传入 naive datetime（如脚本直接 ``datetime.now()``）
            - 直接与 aware datetime 用 ``<`` 比较会抛 ``TypeError``
            - 本方法**只补 tzinfo、不改时钟值**，语义上等同于"以本地默认时区解读 naive 输入"

        :param value: 任意 datetime；naive 视为"以本地默认时区解读"
        :return: aware datetime；不改变时钟值
        边界：
            - naive 使用 ``django_timezone.make_aware`` 附加当前默认时区
            - aware 原样返回（不做跨时区换算）
            - Django ``make_aware`` 遇到夏令时歧义会抛 ``AmbiguousTimeError``；
              本项目环境（UTC+8）无夏令时，理论上不会命中
        """
        if value.tzinfo is None:
            return django_timezone.make_aware(value, django_timezone.get_current_timezone())
        return value


# ----------------------------------------------------------------------
# 对外模块级快捷入口
# ----------------------------------------------------------------------


def ingest_summary(
    db_type: DBType,
    dimension: StrStructuredEnum,
    bk_biz_id: int,
    cluster_domain: str,
    report_time: datetime,
    summary: str = "",
    detail_url: str = "",
    score: Optional[float] = None,
) -> PortraitDimensionSummary:
    """对外模块级快捷函数；等价于 ``PortraitIngestSDK().ingest(**kwargs)``。

    面向巡检维度开发者的**推荐调用方式**，参数含义与 :meth:`PortraitIngestSDK.ingest` 完全一致。

    :param db_type: :class:`DBType` 枚举成员（如 ``DBType.MySQL``）
    :param dimension: 具体 DB 的 ``*PortraitDimensionCode`` 枚举成员
    :param bk_biz_id: 业务 ID
    :param cluster_domain: 集群域名
    :param report_time: 巡检产出时间；**必须 >= 目标集群 ``create_at``**
    :param summary: 摘要文本（默认空字符串）
    :param detail_url: 详情页链接（默认空字符串）
    :param score: 摘要结果分数（默认 None）
    :return: 新落库的 :class:`PortraitDimensionSummary` 实例
    边界 / 异常：同 :meth:`PortraitIngestSDK.ingest`
    """
    return PortraitIngestSDK().ingest(
        db_type=db_type,
        dimension=dimension,
        bk_biz_id=bk_biz_id,
        cluster_domain=cluster_domain,
        report_time=report_time,
        summary=summary,
        detail_url=detail_url,
        score=score,
    )
