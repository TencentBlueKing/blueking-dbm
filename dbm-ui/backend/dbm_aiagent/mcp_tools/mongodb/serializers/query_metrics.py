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


class MongoMetricsInputSerializer(serializers.Serializer):
    """MongoDB 指标查询入参：时间范围、集群、可选实例主机"""

    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    cluster_domain = serializers.CharField(help_text=_("集群域名 cluster_domain"))
    instance_host = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text=_("可选。实例主机 IP，用于按主机过滤指标"),
    )

    def validate(self, attrs):
        if attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError(_("开始时间必须小于结束时间"))
        return attrs


class MongoMetricsOutputSerializer(serializers.Serializer):
    """MongoDB 指标查询通用输出：Markdown 表格形式的指标数据"""

    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    metric_type = serializers.CharField(help_text=_("指标类型：qps/connections/locks/cpu_usage"))
    table = serializers.CharField(
        help_text=_(
            "Markdown 表格：统计汇总（维度 + min/max/avg/max_time）；"
            "instant 查询时为 value/time 表；"
            "数据点 ≤ 120 时在汇总表后追加每个 series 的详细数据点表"
        )
    )
    reminder = serializers.CharField(required=False, allow_blank=True, help_text=_("数据量过大或时间范围过早等提示信息"))
    error = serializers.CharField(required=False, allow_blank=True, help_text=_("错误信息（仅失败时返回）"))
    token_count = serializers.IntegerField(
        required=False,
        help_text=_("响应体估算的 token 数量（便于控制上下文长度）"),
    )
