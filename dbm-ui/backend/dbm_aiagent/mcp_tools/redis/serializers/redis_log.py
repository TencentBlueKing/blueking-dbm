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


class RedisSlowlogInputSerializer(serializers.Serializer):
    """Redis慢查询输入序列化器"""

    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))


class RedisSlowlog4HostInputSerializer(serializers.Serializer):
    """Redis慢查询输入序列化器"""

    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    ip = serializers.CharField(help_text=_("主机IP"))


class RedisSlowlog4InstInputSerializer(serializers.Serializer):
    """Redis慢查询输入序列化器"""

    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    host = serializers.CharField(help_text=_("主机IP"))
    port = serializers.IntegerField(help_text=_("实例端口"))


class RedisSlowlogEntrySerializer(serializers.Serializer):
    """Redis慢查询日志条目"""

    create_time = serializers.CharField(help_text=_("执行时间"))
    duration_us = serializers.IntegerField(help_text=_("执行耗时（微秒）"))
    # duration_ms = serializers.FloatField(help_text=_("执行耗时（毫秒）"))
    cmd = serializers.CharField(help_text=_("命令"))
    key = serializers.CharField(help_text=_("KEY"))
    args = serializers.ListField(child=serializers.CharField(), help_text=_("参数"))
    instance_addr = serializers.CharField(help_text=_("实例地址"))
    instance_role = serializers.CharField(help_text=_("实例角色"))


class RedisSlowlogResponseSerializer(serializers.Serializer):
    """Redis慢查询响应序列化器"""

    total_count = serializers.IntegerField(help_text=_("慢查询日志总数"))
    slowlog_entries = RedisSlowlogEntrySerializer(many=True, help_text=_("慢查询日志列表"))


class RedisSlowlogEntrySerializer(serializers.Serializer):
    """Redis慢查询日志条目"""

    create_time = serializers.CharField(help_text=_("执行时间"))
    duration_us = serializers.IntegerField(help_text=_("执行耗时（微秒）"))
    cmd = serializers.CharField(help_text=_("命令"))
    key = serializers.CharField(help_text=_("KEY"))
    args = serializers.ListField(child=serializers.CharField(), help_text=_("参数"))
    instance_addr = serializers.CharField(help_text=_("实例地址"))
    instance_role = serializers.CharField(help_text=_("实例角色"))


class DurationStatsSerializer(serializers.Serializer):
    """耗时统计信息"""

    max_ms = serializers.FloatField(help_text=_("最大耗时（毫秒）"))
    min_ms = serializers.FloatField(help_text=_("最小耗时（毫秒）"))
    avg_ms = serializers.FloatField(help_text=_("平均耗时（毫秒）"))
    median_ms = serializers.FloatField(help_text=_("中位数耗时（毫秒）"))


class SlowestQuerySerializer(serializers.Serializer):
    """最慢查询信息"""

    cmd = serializers.CharField(help_text=_("命令"))
    key = serializers.CharField(help_text=_("KEY"))
    duration_ms = serializers.FloatField(help_text=_("耗时（毫秒）"))
    create_time = serializers.CharField(help_text=_("执行时间"))


class InstanceStatsSerializer(serializers.Serializer):
    """实例维度统计信息"""

    total_count = serializers.IntegerField(help_text=_("慢日志总条数"))
    duration_stats = DurationStatsSerializer(help_text=_("耗时统计"))
    top_commands = serializers.DictField(child=serializers.IntegerField(), help_text=_("Top命令列表"))
    slowest_query = SlowestQuerySerializer(help_text=_("最慢查询"))


class SummaryStatsSerializer(serializers.Serializer):
    """全局统计摘要"""

    total_count = serializers.IntegerField(help_text=_("总记录数"))
    instance_count = serializers.IntegerField(help_text=_("实例数量"))
    duration_stats = DurationStatsSerializer(help_text=_("耗时统计"))
    top_commands = serializers.DictField(child=serializers.IntegerField(), help_text=_("Top命令列表"))


class RedisSlowClusterStaticSerializer(serializers.Serializer):
    """Redis慢查询分析结果（完整输出）"""

    summary = SummaryStatsSerializer(help_text=_("全局统计摘要"))
    by_instance = serializers.DictField(child=InstanceStatsSerializer(), help_text=_("按实例维度统计（实例地址: 统计信息）"))
