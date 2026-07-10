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
    - 所有失败路径统一抛出 :class:`PortraitInvalidPayloadException`，不吞异常

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

from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import DBType
from backend.db_report.models.portrait_dimension_summary import PortraitDimensionSummary
from backend.db_report.portrait.exceptions import PortraitInvalidPayloadException
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
        - db_type 不是 :class:`DBType` 成员                 -> :class:`PortraitInvalidPayloadException`
        - dimension 不是 :class:`StrStructuredEnum` 成员    -> :class:`PortraitInvalidPayloadException`
        - 已禁用维度（enabled=False）                       -> **不阻塞上报**，正常写入；enabled 只影响读侧
        - 未注册维度                                        -> **自动懒注册**，无异常抛出
        - 其它入参非法（空、超长、类型错）                 -> :class:`PortraitInvalidPayloadException`
        - 数据库写入异常                                    -> 由 Django ORM 抛原生异常，SDK 不吞掉
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
    ) -> PortraitDimensionSummary:
        """写入一条巡检维度摘要。

        执行流程：
            1) 类型校验 + 参数格式校验（:meth:`_validate_payload`）
            2) 从入参 + 枚举提取 (db_type_value, code, name, description)
            3) 注册表懒注册（:meth:`RegistryHelper.ensure_registered`）
            4) 追加写入 :class:`PortraitDimensionSummary` 表

        :param db_type: :class:`DBType` 枚举成员（如 ``DBType.MySQL``）；显式声明所属 DB
        :param dimension: 具体 DB 的 ``*PortraitDimensionCode`` 枚举成员（如 :class:`MysqlPortraitDimensionCode`）
        :param bk_biz_id: CMDB 业务 ID，必须 > 0
        :param cluster_domain: 集群不可变域名，非空
        :param report_time: 本次巡检的业务时间，datetime 类型（精确到秒即可）
        :param summary: 本次巡检的摘要文本；允许为空字符串（视为无风险要点）；单条 <= 4000 字符
        :param detail_url: 本次巡检详情页链接；允许为空；<= 1024 字符
        :return: 新落库的 :class:`PortraitDimensionSummary` 实例（含自增 id）

        边界 / 异常：
            - db_type / dimension 类型错 / 其它入参不合法 -> :class:`PortraitInvalidPayloadException`
            - 维度未注册                                  -> 自动创建注册表记录，然后正常写入
            - 维度已禁用 (enabled=False)                   -> 不影响上报（enabled 只影响 Agent 读侧）
            - DB 写入失败                                 -> Django ORM 原生异常（不由 SDK 转换）
        """
        # 1) 参数校验（快速失败）
        self._validate_payload(
            db_type=db_type,
            dimension=dimension,
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            report_time=report_time,
            summary=summary,
            detail_url=detail_url,
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
    ) -> None:
        """入参格式校验；不合法直接抛出 :class:`PortraitInvalidPayloadException`。

        校验策略：
            - db_type 必须是 :class:`DBType` 成员
            - dimension 必须是 :class:`StrStructuredEnum` 成员（由 IDE 编译期与本运行时兜底共同保证）
            - 其它字段只做**格式类**校验（空 / 类型 / 长度）
            - 一条错误信息即抛出，不做累积（快速失败利于调用方定位）

        :raises PortraitInvalidPayloadException: 任一校验项不通过
        """
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
) -> PortraitDimensionSummary:
    """对外模块级快捷函数；等价于 ``PortraitIngestSDK().ingest(**kwargs)``。

    面向巡检维度开发者的**推荐调用方式**，参数含义与 :meth:`PortraitIngestSDK.ingest` 完全一致。

    :param db_type: :class:`DBType` 枚举成员（如 ``DBType.MySQL``）
    :param dimension: 具体 DB 的 ``*PortraitDimensionCode`` 枚举成员
    :param bk_biz_id: 业务 ID
    :param cluster_domain: 集群域名
    :param report_time: 巡检产出时间
    :param summary: 摘要文本（默认空字符串）
    :param detail_url: 详情页链接（默认空字符串）
    :return: 新落库的 :class:`PortraitDimensionSummary` 实例
    边界：同 :meth:`PortraitIngestSDK.ingest`
    """
    return PortraitIngestSDK().ingest(
        db_type=db_type,
        dimension=dimension,
        bk_biz_id=bk_biz_id,
        cluster_domain=cluster_domain,
        report_time=report_time,
        summary=summary,
        detail_url=detail_url,
    )
