# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像 MCP - 出/入参 Serializer。

模块职责：
    - 定义 ``portrait_discover_dimensions`` / ``portrait_fetch_summaries`` 两个 MCP 工具的
      请求 / 响应结构，供装饰器 ``mcp_tools_api_decorator`` 引用
    - 严格声明每个字段的语义与 help_text，保证 Agent / OpenAPI 侧提示准确
"""
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_report.enums import SummaryFetchStrategy

# ----------------------------------------------------------------------
# 通用嵌套结构
# ----------------------------------------------------------------------


class PortraitDimensionSerializer(serializers.Serializer):
    """单个维度注册信息（discover 出参元素）。"""

    db_type = serializers.CharField(help_text=_("数据库类型，取值同 DBType 枚举"))
    dimension_code = serializers.CharField(help_text=_("维度短码，同 db_type 下唯一"))
    name = serializers.CharField(help_text=_("维度中文名称"))
    description = serializers.CharField(help_text=_("维度描述文本；用于告诉 Agent 该维度关注什么"), allow_blank=True)
    weight = serializers.FloatField(
        help_text=_("该维度在画像综合评分中的计算权重；未配置时为 null"),
        allow_null=True,
        required=False,
    )
    summary_fetch_strategy = serializers.ChoiceField(
        choices=SummaryFetchStrategy.get_choices(),
        help_text=_("获取该维度摘要结果的策略：all 返回全部 / last 返回最新一条 / first 返回最老一条"),
        # 与模型层 PortraitDimensionRegistry.summary_fetch_strategy 的 default 严格对齐：
        # - 模型层 null=False + default="all"，DB 层不会出现 NULL；
        # - Serializer 兜底 default 用于两类边界：
        #   1) 未来若本 Serializer 被复用为入参（如管理侧编辑维度），允许缺省；
        #   2) 极端场景下数据迁移遗漏 / 直接 SQL 写入产生空值时的防御性兜底；
        # - 不加 allow_null=True：模型语义不允许 null，避免向下游 Agent 传递虚假的 null 分支。
        required=False,
        default=SummaryFetchStrategy.ALL.value,
    )


class PortraitSummarySerializer(serializers.Serializer):
    """单个维度的最新摘要（fetch_summaries 出参元素）。"""

    db_type = serializers.CharField(help_text=_("数据库类型"))
    dimension_code = serializers.CharField(help_text=_("维度短码"))
    name = serializers.CharField(help_text=_("维度中文名称（来自注册表）"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    cluster_domain = serializers.CharField(help_text=_("集群不可变域名"))
    report_time = serializers.DateTimeField(help_text=_("本次巡检产出的业务时间（精确到秒）"))
    summary = serializers.CharField(help_text=_("巡检摘要文本"), allow_blank=True)
    detail_url = serializers.CharField(help_text=_("巡检详情页链接，供用户点击查看完整报告"), allow_blank=True)
    score = serializers.FloatField(
        help_text=_("该条摘要结果的分数；未上报时为 null"),
        allow_null=True,
        required=False,
    )


# ----------------------------------------------------------------------
# 工具 1：discover_dimensions
# ----------------------------------------------------------------------


class PortraitDiscoverDimensionsInputSerializer(serializers.Serializer):
    """discover 入参：通过 (bk_biz_id, cluster_domain) 反查集群 db_type，进而返回该集群启用的巡检维度清单。

    契约：
        - **不再由调用方传 db_type**：db_type 由服务端通过 (bk_biz_id, cluster_domain)
          反查集群元数据得到（见 ``PortraitQueryService.resolve_cluster``），
          与 ``ingest_summary`` / ``fetch_summaries`` 保持"集群 -> db_type"唯一事实源
        - 两个字段均为必填；成对使用，避免跨业务泄漏
    """

    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID；必须为正整数"), min_value=1)
    cluster_domain = serializers.CharField(help_text=_("集群不可变主域名"))


class PortraitDiscoverDimensionsOutputSerializer(serializers.Serializer):
    """discover 出参：目标集群 db_type 下启用中的维度列表。

    可预期分支通过 ``status`` 字段表达，不抛异常给前端。
    """

    status = serializers.ChoiceField(
        choices=[
            ("ok", _("查询成功")),
            ("cluster_not_found", _("集群不存在或不属于该业务")),
        ],
        help_text=_("查询结果状态；ok 表示成功，其余为可预期失败分支"),
    )
    db_type = serializers.CharField(
        help_text=_("回显服务端反查得到的 db_type；失败分支为空串"),
        allow_blank=True,
        default="",
    )
    dimensions = serializers.ListField(
        child=PortraitDimensionSerializer(),
        help_text=_("该集群 db_type 下所有启用中的维度信息（enabled=True）；失败分支为空列表"),
    )


# ----------------------------------------------------------------------
# 工具 2：fetch_summaries
# ----------------------------------------------------------------------


class PortraitFetchSummariesInputSerializer(serializers.Serializer):
    """fetch_summaries 入参：集群 + 可选维度过滤 + 可选时间窗。"""

    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    cluster_domain = serializers.CharField(help_text=_("集群不可变域名"))
    dimension_codes = serializers.ListField(
        child=serializers.CharField(),
        help_text=_("维度短码列表；不传表示读取该集群 db_type 下的全部启用维度"),
        required=False,
        allow_null=True,
        allow_empty=True,
        default=None,
    )
    since = serializers.DateTimeField(
        help_text=_("摘要时间下界（含）；不传表示不限"),
        required=False,
        allow_null=True,
        default=None,
    )
    until = serializers.DateTimeField(
        help_text=_("摘要时间上界（含）；不传表示不限"),
        required=False,
        allow_null=True,
        default=None,
    )


class PortraitFetchSummariesOutputSerializer(serializers.Serializer):
    """fetch_summaries 出参：返回 effective 时间窗内所有匹配的摘要（不做去重）。

    可预期分支通过 ``status`` 字段表达，不抛异常给前端。Agent 判断口径：
        - ``status="cluster_not_found"``：集群不存在 / 不属于该业务；db_type 为空、cluster_created_at 为 null
        - ``status="time_range_before_cluster_created"``：用户区间完全早于集群创建时间；summaries 必为空
        - ``status="invalid_time_range"``：since > until，语义不成立
        - ``status="ok"`` + ``summaries=[]``：集群存在但 effective 时间窗内 0 条数据
        - ``status="ok"`` + ``missing_codes`` 非空：部分 code 在 effective 时间窗内 0 条数据
        - ``effective_since`` 与用户传的 ``since`` 不同 -> 说明被服务端上调至 ``cluster_created_at``
          以规避"上一代同域名集群"的脏数据；Agent 应向用户显式说明
    """

    status = serializers.ChoiceField(
        choices=[
            ("ok", _("查询成功（可能 summaries 为空，代表集群存在但时间窗无数据）")),
            ("cluster_not_found", _("集群不存在或不属于该业务")),
            ("time_range_before_cluster_created", _("查询区间完全早于集群创建时间；无有效数据")),
            ("invalid_time_range", _("since > until，时间区间语义不成立")),
        ],
        help_text=_("查询结果状态；用于 Agent 区分「集群不存在」「区间不合法」「集群存在但无数据」等分支"),
    )
    db_type = serializers.CharField(
        help_text=_("回显服务端反查得到的 db_type；集群不存在分支为空串"),
        allow_blank=True,
        default="",
    )
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    cluster_domain = serializers.CharField(help_text=_("集群不可变域名"))
    cluster_created_at = serializers.DateTimeField(
        help_text=_("集群创建时间（``Cluster.create_at``）；作为脏数据物理下界；cluster_not_found 分支为 null"),
        allow_null=True,
        required=False,
    )
    effective_since = serializers.DateTimeField(
        help_text=_(
            "服务端实际使用的时间下界；等于 ``max(用户 since, cluster_created_at)``，" "用于规避上一代同域名集群的脏数据；cluster_not_found 分支为 null"
        ),
        allow_null=True,
        required=False,
    )
    effective_until = serializers.DateTimeField(
        help_text=_("服务端实际使用的时间上界；不限时为 null"),
        allow_null=True,
        required=False,
    )
    summaries = serializers.ListField(
        child=PortraitSummarySerializer(),
        help_text=_(
            "effective 时间窗内所有匹配的巡检摘要列表，不做「每 code 取最新」的聚合；" "同一 code 在时间窗内有 N 次上报即返回 N 条；按 (code 升序, report_time 升序) 排列"
        ),
    )
    missing_codes = serializers.ListField(
        child=serializers.CharField(),
        help_text=_("在 effective 时间窗内 0 条摘要数据的维度 code 列表；供 Agent 提示"),
    )


# ----------------------------------------------------------------------
# 工具 3：ingest_summary（写侧）
# ----------------------------------------------------------------------


class PortraitIngestSummaryInputSerializer(serializers.Serializer):
    """ingest_summary 入参：写入一条集群维度巡检摘要。

    契约：
        - **不再由调用方传 db_type**：db_type 由服务端通过 (bk_biz_id, cluster_domain)
          反查集群元数据得到（见 ``PortraitQueryService.resolve_cluster``），
          既避免调用方与集群元数据出现口径不一致，又能省一个易错入参
        - ``dimension_code`` 必须是所反查 db_type 下已定义的 ``*PortraitDimensionCode`` 枚举 value
        - ``report_time`` 为 datetime 格式（ISO8601 字符串亦可），精确到秒
        - ``summary`` <= 4000 字符；``detail_url`` <= 1024 字符
    """

    dimension_code = serializers.CharField(help_text=_("维度短码；须为该集群 db_type 下已定义的维度枚举 value，如 slow_query"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID；必须为正整数"), min_value=1)
    cluster_domain = serializers.CharField(help_text=_("集群不可变主域名"))
    report_time = serializers.DateTimeField(help_text=_("本次巡检的业务时间；精确到秒"))
    summary = serializers.CharField(
        help_text=_("巡检摘要文本；允许为空；单条 <= 4000 字符"),
        required=False,
        allow_blank=True,
        default="",
        max_length=4000,
    )
    detail_url = serializers.CharField(
        help_text=_("本次巡检详情页链接；允许为空；<= 1024 字符"),
        required=False,
        allow_blank=True,
        default="",
        max_length=1024,
    )
    score = serializers.FloatField(
        help_text=_("本次摘要结果的分数；允许为空（null 表示未上报）"),
        required=False,
        allow_null=True,
        default=None,
    )


class PortraitIngestSummaryOutputSerializer(serializers.Serializer):
    """ingest_summary 出参：可预期分支通过 ``status`` 字段表达，不抛异常给前端。"""

    status = serializers.ChoiceField(
        choices=[
            ("ok", _("写入成功")),
            ("cluster_not_found", _("集群不存在或不属于该业务")),
            ("unsupported_db_type", _("集群 db_type 暂未接入画像维度枚举")),
            ("invalid_code", _("dimension_code 在该集群 db_type 下未定义")),
            ("invalid_payload", _("其它入参不合法（空/类型/超长等）")),
        ],
        help_text=_("写入结果状态；ok 表示成功，其余为可预期失败分支"),
    )
    id = serializers.IntegerField(
        help_text=_("新落库记录的自增 id；仅 status=ok 时有效，其它分支为 0"),
        required=False,
        default=0,
    )
    db_type = serializers.CharField(
        help_text=_("回显服务端反查得到的 db_type；失败分支可能为空"),
        allow_blank=True,
        default="",
    )
    dimension_code = serializers.CharField(help_text=_("回显 dimension_code"), allow_blank=True, default="")
    message = serializers.CharField(
        help_text=_("附加信息；失败分支会填充可读的错误原因，成功分支为空"),
        allow_blank=True,
        default="",
    )
