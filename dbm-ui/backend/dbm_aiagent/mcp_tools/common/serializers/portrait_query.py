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

# ----------------------------------------------------------------------
# 通用嵌套结构
# ----------------------------------------------------------------------


class PortraitDimensionSerializer(serializers.Serializer):
    """单个维度注册信息（discover 出参元素）。"""

    db_type = serializers.CharField(help_text=_("数据库类型，取值同 DBType 枚举"))
    code = serializers.CharField(help_text=_("维度短码，同 db_type 下唯一"))
    name = serializers.CharField(help_text=_("维度中文名称"))
    description = serializers.CharField(help_text=_("维度描述文本；用于告诉 Agent 该维度关注什么"), allow_blank=True)


class PortraitSummarySerializer(serializers.Serializer):
    """单个维度的最新摘要（fetch_summaries 出参元素）。"""

    db_type = serializers.CharField(help_text=_("数据库类型"))
    code = serializers.CharField(help_text=_("维度短码"))
    name = serializers.CharField(help_text=_("维度中文名称（来自注册表）"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    cluster_domain = serializers.CharField(help_text=_("集群不可变域名"))
    report_time = serializers.DateTimeField(help_text=_("本次巡检产出的业务时间（精确到秒）"))
    summary = serializers.CharField(help_text=_("巡检摘要文本"), allow_blank=True)
    detail_url = serializers.CharField(help_text=_("巡检详情页链接，供用户点击查看完整报告"), allow_blank=True)


# ----------------------------------------------------------------------
# 工具 1：discover_dimensions
# ----------------------------------------------------------------------


class PortraitDiscoverDimensionsInputSerializer(serializers.Serializer):
    """discover 入参：可选 db_type 过滤。"""

    db_type = serializers.CharField(
        help_text=_("按 DB 类型过滤；不传表示返回全部启用维度"),
        required=False,
        allow_blank=True,
        default="",
    )


class PortraitDiscoverDimensionsOutputSerializer(serializers.Serializer):
    """discover 出参：维度列表。"""

    dimensions = serializers.ListField(
        child=PortraitDimensionSerializer(),
        help_text=_("当前所有启用中的维度信息（enabled=True）"),
    )


# ----------------------------------------------------------------------
# 工具 2：fetch_summaries
# ----------------------------------------------------------------------


class PortraitFetchSummariesInputSerializer(serializers.Serializer):
    """fetch_summaries 入参：集群 + 可选维度过滤 + 可选时间窗。"""

    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    cluster_domain = serializers.CharField(help_text=_("集群不可变域名"))
    codes = serializers.ListField(
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
    """fetch_summaries 出参：返回时间窗内所有匹配的摘要（不做去重）。"""

    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    cluster_domain = serializers.CharField(help_text=_("集群不可变域名"))
    summaries = serializers.ListField(
        child=PortraitSummarySerializer(),
        help_text=_("时间窗内所有匹配的巡检摘要列表，不做「每 code 取最新」的聚合；" "同一 code 在时间窗内有 N 次上报即返回 N 条；按 (code 升序, report_time 升序) 排列"),
    )
    missing_codes = serializers.ListField(
        child=serializers.CharField(),
        help_text=_("在时间窗内 0 条摘要数据的维度 code 列表；供 Agent 提示"),
    )
