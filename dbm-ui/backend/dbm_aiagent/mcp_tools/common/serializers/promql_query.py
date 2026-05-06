# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class PromQLFilterSerializer(serializers.Serializer):
    """PromQL 标签过滤条件"""

    label_op_choices = [
        ("equal", _("等于")),
        ("not_equal", _("不等于")),
        ("match", _("正则匹配")),
        ("not_match", _("正则不匹配")),
    ]

    label = serializers.CharField(
        help_text=_("标签名称，" "cluster_domain/instance/instance_role 过滤条件默认会注入，不需要重复在 filter 里指定")
    )
    op = serializers.ChoiceField(choices=label_op_choices, help_text=_("匹配操作符"))
    value = serializers.CharField(help_text=_("标签值，多个值时用|连接，例如 value1|value2"))


class PromQLQueryInputSerializer(serializers.Serializer):

    """通用 PromQL 指标查询输入参数"""

    aggregation_choices = [
        ("max", _("最大值")),
        ("min", _("最小值")),
        ("sum", _("求和")),
        ("avg", _("平均值")),
        ("count", _("计数")),
    ]

    range_function_choices = [
        ("max", _("时间窗口内最大值 max_over_time（适用于 Gauge 指标如 CPU、内存）")),
        ("min", _("时间窗口内最小值 min_over_time（适用于 Gauge 指标如 CPU、内存）")),
        ("sum", _("时间窗口内求和 sum_over_time（适用于 Gauge 指标）")),
        ("avg", _("时间窗口内平均值 avg_over_time（适用于 Gauge 指标如 CPU、内存）")),
        ("rate", _("计算 Counter 指标的每秒速率 rate（适用于 QPS、请求数等单调递增指标）")),
        ("increase", _("计算 Counter 指标的增量 increase（适用于 QPS、请求数等单调递增指标）")),
        ("count", _("时间窗口内计数 count_over_time（适用于 Gauge 指标）")),
    ]

    cluster_domain = serializers.CharField(required=True, help_text=_("集群域名"))

    metric_name = serializers.CharField(help_text=_("指标名称，如 cpu_summary:usage, mysql_global_status_questions"))

    filters = PromQLFilterSerializer(
        many=True,
        required=False,
        default=[],
        help_text=_("label 过滤条件"),
    )
    group_by = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=[],
        help_text=_("分组标签列表，如 ['cluster_domain', 'instance_role']"),
    )
    aggregation = serializers.ChoiceField(
        choices=aggregation_choices,
        required=False,
        default=None,
        allow_null=True,
        help_text=_("外层聚合函数: max/min/sum/avg/count"),
    )
    range_function = serializers.ChoiceField(
        choices=range_function_choices,
        required=False,
        default=None,
        allow_null=True,
        help_text=_(
            "应用于时间窗口的 range function。"
            "Gauge 类指标（如 CPU、内存使用率）使用: max/min/sum/avg/count（对应 *_over_time）；"
            "Counter 类指标（如 QPS、慢查询数等单调递增指标）使用: rate（每秒速率）/increase（增量）"
        ),
    )
    start_time = serializers.DateTimeField(
        required=False,
        default=None,
        allow_null=True,
        help_text=_("开始时间，时间格式 2026-01-08T16:33:38+08:00，默认为 end_time 前 5 分钟"),
    )
    end_time = serializers.DateTimeField(
        required=False,
        default=None,
        allow_null=True,
        help_text=_("结束时间，时间格式 2026-01-08T16:33:38+08:00，默认为当前时间"),
    )
    step = serializers.CharField(
        required=False,
        default="1m",
        help_text=_("查询步长(resolution)，如 '1m', '5m', '1h'，默认 '1m'"),
    )


class PromQLSeriesItemSerializer(serializers.Serializer):
    """单条时序数据"""

    dimensions = serializers.DictField(help_text=_("维度标签"))
    target = serializers.CharField(help_text=_("目标标识"))
    datapoints = serializers.ListField(help_text=_("时序数据点列表，每项为 [value, timestamp]"))
    unit = serializers.CharField(help_text=_("单位"), required=False, default="")


class PromQLQueryOutputSerializer(serializers.Serializer):
    """通用 PromQL 指标查询输出"""

    promql = serializers.CharField(help_text=_("实际执行的 PromQL 查询语句"))
    series = PromQLSeriesItemSerializer(many=True, help_text=_("时序数据列表"))


class QueryMetricByRoleInputSerializer(PromQLQueryInputSerializer):
    """按角色查询 PromQL 指标，自动将 cluster_domain 和 instance_roles 注入 filters"""

    instance_role = serializers.ListField(
        child=serializers.CharField(),
        required=True,
        help_text=_("实例角色列表，如 ['backend_master', 'backend_slave']"),
    )


class QueryMetricByInstanceInputSerializer(PromQLQueryInputSerializer):
    """按实例查询 PromQL 指标，自动将 cluster_domain 和 instances 注入 filters"""

    instance = serializers.ListField(
        child=serializers.CharField(),
        required=True,
        help_text=_("实例地址列表，如 ['127.0.0.1:3306', '127.0.0.2:3306']"),
    )
