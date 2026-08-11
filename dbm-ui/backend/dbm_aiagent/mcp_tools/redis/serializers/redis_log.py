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


class RedisSlowlogQueryInputSerializer(serializers.Serializer):
    """Redis 慢查询日志查询输入序列化器"""

    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    ip = serializers.CharField(help_text=_("主机IP，不传则查询整个集群的统计数据"), required=False, allow_null=True)
    port = serializers.IntegerField(help_text=_("实例端口，配合IP使用，不传则查询整台机器"), required=False, allow_null=True)


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


# ---- 大key日志序列化器 ----


class RedisBigkeyInputSerializer(serializers.Serializer):
    """Redis大key日志查询输入序列化器（集群维度）"""

    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))


class RedisBigkey4HostInputSerializer(serializers.Serializer):
    """Redis大key日志查询输入序列化器（主机/实例维度，port 可选）"""

    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    ip = serializers.CharField(help_text=_("主机IP"))
    port = serializers.IntegerField(help_text=_("实例端口，不传则查询整台机器"), required=False, allow_null=True)


class RedisBigkeyQueryInputSerializer(serializers.Serializer):
    """Redis大key日志查询输入序列化器"""

    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    ip = serializers.CharField(help_text=_("主机IP，不传则查询整个集群的统计数据"), required=False, allow_null=True)
    port = serializers.IntegerField(help_text=_("实例端口，配合IP使用，不传则查询整台机器"), required=False, allow_null=True)


class RedisBigkeyEntrySerializer(serializers.Serializer):
    """单条大key日志条目"""

    addr = serializers.CharField(help_text=_("实例地址（ip:port）"))
    key = serializers.CharField(help_text=_("Key名称"))
    valsize = serializers.IntegerField(help_text=_("Value大小（字节）"))
    valsize_human = serializers.CharField(help_text=_("Value大小（可读格式）"))
    type = serializers.CharField(help_text=_("Key类型（string/hash/list/set/zset）"))
    sortby = serializers.CharField(help_text=_("排序方式（sortBySize/sortByFileds）"))
    top_idx = serializers.IntegerField(help_text=_("Top排名索引"))
    fields = serializers.IntegerField(help_text=_("字段数量（hash/list/set/zset有效）"))
    timestamp = serializers.CharField(help_text=_("记录时间"))
    domain = serializers.CharField(help_text=_("集群域名"))


class RedisBigkeyResponseSerializer(serializers.Serializer):
    """大key日志列表响应序列化器"""

    total_count = serializers.IntegerField(help_text=_("大key日志总数"))
    bigkey_entries = RedisBigkeyEntrySerializer(many=True, help_text=_("大key日志列表（按valsize降序）"))


class RedisBigkeyInstanceStatsSerializer(serializers.Serializer):
    """单实例大key统计信息"""

    total_count = serializers.IntegerField(help_text=_("大key总条数"))
    total_size = serializers.IntegerField(help_text=_("大key总大小（字节）"))
    total_size_human = serializers.CharField(help_text=_("大key总大小（可读格式）"))
    type_distribution = serializers.DictField(child=serializers.IntegerField(), help_text=_("Key类型分布"))
    top_keys = RedisBigkeyEntrySerializer(many=True, help_text=_("Top10大key列表（按valsize降序）"))


class RedisBigkeySummarySerializer(serializers.Serializer):
    """大key全局统计摘要"""

    total_count = serializers.IntegerField(help_text=_("大key总条数"))
    instance_count = serializers.IntegerField(help_text=_("涉及实例数量"))
    total_size = serializers.IntegerField(help_text=_("大key总大小（字节）"))
    total_size_human = serializers.CharField(help_text=_("大key总大小（可读格式）"))
    type_distribution = serializers.DictField(child=serializers.IntegerField(), help_text=_("Key类型分布"))


class RedisBigkeyClusterStaticSerializer(serializers.Serializer):
    """Redis大key分析结果（集群维度完整输出）"""

    summary = RedisBigkeySummarySerializer(help_text=_("全局统计摘要"))
    by_instance = serializers.DictField(child=RedisBigkeyInstanceStatsSerializer(), help_text=_("按实例维度统计（实例地址: 统计信息）"))


# ---- server log 序列化器 ----


class RedisServerlogInputSerializer(serializers.Serializer):
    """Redis server log 查询输入序列化器（集群维度）"""

    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))


class RedisServerlog4HostInputSerializer(serializers.Serializer):
    """Redis server log 查询输入序列化器（主机/实例维度，port 可选）"""

    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    ip = serializers.CharField(help_text=_("主机IP"))
    port = serializers.IntegerField(help_text=_("实例端口，不传则查询整台机器"), required=False, allow_null=True)


class RedisServerlogQueryInputSerializer(serializers.Serializer):
    """Redis server log 查询输入序列化器"""

    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    ip = serializers.CharField(help_text=_("主机IP，不传则查询整个集群的统计数据"), required=False, allow_null=True)
    port = serializers.IntegerField(help_text=_("实例端口，配合IP使用，不传则查询整台机器"), required=False, allow_null=True)


class RedisServerlogEntrySerializer(serializers.Serializer):
    """单条 server log 日志条目"""

    server_ip = serializers.CharField(help_text=_("服务器IP"))
    server_port = serializers.IntegerField(help_text=_("服务器端口"))
    addr = serializers.CharField(help_text=_("实例地址（ip:port）"))
    domain = serializers.CharField(help_text=_("集群域名"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    role = serializers.CharField(help_text=_("实例角色（如 twemproxy/redis）"))
    log_file = serializers.CharField(help_text=_("日志文件路径"))
    data = serializers.CharField(help_text=_("日志内容"))
    time_zone = serializers.CharField(help_text=_("时区"))
    create_time = serializers.CharField(help_text=_("日志时间"))


class RedisServerlogResponseSerializer(serializers.Serializer):
    """server log 日志列表响应序列化器"""

    total_count = serializers.IntegerField(help_text=_("日志总数"))
    log_entries = RedisServerlogEntrySerializer(many=True, help_text=_("日志列表"))


class RedisServerlogInstanceStatsSerializer(serializers.Serializer):
    """单实例 server log 统计信息"""

    total_count = serializers.IntegerField(help_text=_("日志总条数"))
    role = serializers.CharField(help_text=_("实例角色"))
    log_files = serializers.ListField(child=serializers.CharField(), help_text=_("涉及日志文件列表"))
    latest_logs = RedisServerlogEntrySerializer(many=True, help_text=_("最新10条日志"))


class RedisServerlogSummarySerializer(serializers.Serializer):
    """server log 全局统计摘要"""

    total_count = serializers.IntegerField(help_text=_("日志总条数"))
    instance_count = serializers.IntegerField(help_text=_("涉及实例数量"))
    role_distribution = serializers.DictField(child=serializers.IntegerField(), help_text=_("角色分布"))


class RedisServerlogClusterStaticSerializer(serializers.Serializer):
    """Redis server log 分析结果（集群维度完整输出）"""

    summary = RedisServerlogSummarySerializer(help_text=_("全局统计摘要"))
    by_instance = serializers.DictField(
        child=RedisServerlogInstanceStatsSerializer(), help_text=_("按实例维度统计（实例地址: 统计信息）")
    )


# ---- 热key日志序列化器 ----


class RedisHotkeyQueryInputSerializer(serializers.Serializer):
    """Redis 热key日志查询输入序列化器"""

    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    ip = serializers.CharField(help_text=_("主机IP，不传则查询整个集群的统计数据"), required=False, allow_null=True)
    port = serializers.IntegerField(help_text=_("实例端口，配合IP使用，不传则查询整台机器"), required=False, allow_null=True)


class RedisHotkeyEntrySerializer(serializers.Serializer):
    """单条热key日志条目"""

    addr = serializers.CharField(help_text=_("实例地址（ip:port）"))
    key_sample = serializers.CharField(help_text=_("热key示例"))
    key_cnt = serializers.IntegerField(help_text=_("采样命中的key数量"))
    key_ops = serializers.IntegerField(help_text=_("key访问频次（次数越大越热）"))
    key_ratio = serializers.FloatField(help_text=_("该key在总请求中的占比"))
    timestamp = serializers.CharField(help_text=_("记录时间"))
    domain = serializers.CharField(help_text=_("集群域名"))


class RedisHotkeyResponseSerializer(serializers.Serializer):
    """热key日志列表响应序列化器"""

    total_count = serializers.IntegerField(help_text=_("热key日志总数"))
    hotkey_entries = RedisHotkeyEntrySerializer(many=True, help_text=_("热key日志列表（按key_ops降序）"))


class RedisHotkeyInstanceStatsSerializer(serializers.Serializer):
    """单实例热key统计信息"""

    total_count = serializers.IntegerField(help_text=_("热key总条数"))
    total_ops = serializers.IntegerField(help_text=_("热key累计访问次数"))
    top_keys = RedisHotkeyEntrySerializer(many=True, help_text=_("Top10热key列表（按key_ops降序）"))


class RedisHotkeySummarySerializer(serializers.Serializer):
    """热key全局统计摘要"""

    total_count = serializers.IntegerField(help_text=_("热key总条数"))
    instance_count = serializers.IntegerField(help_text=_("涉及实例数量"))
    total_ops = serializers.IntegerField(help_text=_("热key累计访问次数"))


class RedisHotkeyClusterStaticSerializer(serializers.Serializer):
    """Redis 热key分析结果（集群维度完整输出）"""

    summary = RedisHotkeySummarySerializer(help_text=_("全局统计摘要"))
    by_instance = serializers.DictField(child=RedisHotkeyInstanceStatsSerializer(), help_text=_("按实例维度统计（实例地址: 统计信息）"))
