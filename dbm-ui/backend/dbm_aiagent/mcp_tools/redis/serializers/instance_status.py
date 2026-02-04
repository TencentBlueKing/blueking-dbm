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

# ==================== 输入序列化器 ====================


class RedisInstanceInputSerializer(serializers.Serializer):
    """Redis实例输入序列化器"""

    redis_addr = serializers.CharField(help_text=_("实例地址"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))


# ==================== 输出序列化器 ====================


class RedisClientInfoSerializer(serializers.Serializer):
    """单个Redis客户端信息"""

    id = serializers.CharField(help_text=_("客户端唯一ID"))
    addr = serializers.CharField(help_text=_("客户端地址（IP:端口）"))
    fd = serializers.IntegerField(help_text=_("文件描述符"))
    name = serializers.CharField(help_text=_("客户端名称"), allow_blank=True)
    age = serializers.IntegerField(help_text=_("连接存活时间（秒）"))
    idle = serializers.IntegerField(help_text=_("空闲时间（秒）"))
    flags = serializers.CharField(help_text=_("客户端标志"))
    db = serializers.IntegerField(help_text=_("当前数据库索引"))
    sub = serializers.IntegerField(help_text=_("订阅的频道数"))
    psub = serializers.IntegerField(help_text=_("订阅的模式数"))
    multi = serializers.IntegerField(help_text=_("事务中的命令数"))
    qbuf = serializers.IntegerField(help_text=_("查询缓冲区长度"))
    qbuf_free = serializers.IntegerField(help_text=_("查询缓冲区剩余空间"))
    obl = serializers.IntegerField(help_text=_("输出缓冲区长度"))
    oll = serializers.IntegerField(help_text=_("输出列表长度"))
    omem = serializers.IntegerField(help_text=_("输出缓冲区内存使用"))
    events = serializers.CharField(help_text=_("文件描述符事件"))
    cmd = serializers.CharField(help_text=_("最后执行的命令"), allow_blank=True)


class RedisClientListResponseSerializer(serializers.Serializer):
    """Redis客户端列表响应"""

    total_clients = serializers.IntegerField(help_text=_("客户端总数"))
    clients = RedisClientInfoSerializer(many=True, help_text=_("客户端列表"))


class RedisCommandStatsSerializer(serializers.Serializer):
    """单个命令的统计信息"""

    command = serializers.CharField(help_text=_("命令名称"))
    calls = serializers.IntegerField(help_text=_("调用次数"))
    usec = serializers.IntegerField(help_text=_("总耗时（微秒）"))
    usec_per_call = serializers.FloatField(help_text=_("平均耗时（微秒）"))
    rejected_calls = serializers.IntegerField(help_text=_("拒绝次数"), required=False)
    failed_calls = serializers.IntegerField(help_text=_("失败次数"), required=False)


class RedisCommandStatsDeltaSerializer(serializers.Serializer):
    """命令统计增量信息（1秒间隔）"""

    command = serializers.CharField(help_text=_("命令名称"))
    calls_per_sec = serializers.IntegerField(help_text=_("每秒调用次数"))
    usec_per_sec = serializers.IntegerField(help_text=_("每秒总耗时（微秒）"))
    avg_usec_per_call = serializers.FloatField(help_text=_("平均每次调用耗时（微秒）"))


class RedisCommandStatsResponseSerializer(serializers.Serializer):
    """Redis命令统计响应"""

    sample_interval = serializers.FloatField(help_text=_("采样间隔（秒）"))
    total_commands = serializers.IntegerField(help_text=_("命令种类总数"))
    total_calls_per_sec = serializers.IntegerField(help_text=_("每秒总调用次数"))
    commands = RedisCommandStatsDeltaSerializer(many=True, help_text=_("命令统计列表"))


class RedisServerInfoSerializer(serializers.Serializer):
    """Redis服务器基本信息"""

    redis_version = serializers.CharField(help_text=_("Redis版本"))
    redis_mode = serializers.CharField(help_text=_("运行模式（standalone/cluster/sentinel）"))
    os = serializers.CharField(help_text=_("操作系统"))
    arch_bits = serializers.IntegerField(help_text=_("架构位数"))
    process_id = serializers.IntegerField(help_text=_("进程ID"))
    tcp_port = serializers.IntegerField(help_text=_("TCP端口"))
    uptime_in_seconds = serializers.IntegerField(help_text=_("运行时长（秒）"))
    uptime_in_days = serializers.IntegerField(help_text=_("运行时长（天）"))
    hz = serializers.IntegerField(help_text=_("服务器频率"))
    configured_hz = serializers.IntegerField(help_text=_("配置的频率"))


class RedisClientsInfoSerializer(serializers.Serializer):
    """Redis客户端连接信息"""

    connected_clients = serializers.IntegerField(help_text=_("已连接客户端数量"))
    client_recent_max_input_buffer = serializers.IntegerField(help_text=_("客户端最大输入缓冲区"))
    client_recent_max_output_buffer = serializers.IntegerField(help_text=_("客户端最大输出缓冲区"))
    blocked_clients = serializers.IntegerField(help_text=_("阻塞的客户端数量"))
    tracking_clients = serializers.IntegerField(required=False, help_text=_("追踪的客户端数量"))
    clients_in_timeout_table = serializers.IntegerField(required=False, help_text=_("超时表中的客户端数量"))


class RedisMemoryInfoSerializer(serializers.Serializer):
    """Redis内存使用信息"""

    used_memory = serializers.IntegerField(help_text=_("已使用内存（字节）"))
    used_memory_human = serializers.CharField(help_text=_("已使用内存（可读格式）"))
    used_memory_rss = serializers.IntegerField(help_text=_("RSS内存（字节）"))
    used_memory_rss_human = serializers.CharField(help_text=_("RSS内存（可读格式）"))
    used_memory_peak = serializers.IntegerField(help_text=_("内存使用峰值（字节）"))
    used_memory_peak_human = serializers.CharField(help_text=_("内存使用峰值（可读格式）"))
    total_system_memory = serializers.IntegerField(help_text=_("系统总内存（字节）"))
    total_system_memory_human = serializers.CharField(help_text=_("系统总内存（可读格式）"))
    used_memory_lua = serializers.IntegerField(help_text=_("Lua引擎使用内存（字节）"))
    used_memory_lua_human = serializers.CharField(help_text=_("Lua引擎使用内存（可读格式）"))
    maxmemory = serializers.IntegerField(help_text=_("最大内存限制（字节）"))
    maxmemory_human = serializers.CharField(help_text=_("最大内存限制（可读格式）"))
    maxmemory_policy = serializers.CharField(help_text=_("内存淘汰策略"))
    mem_fragmentation_ratio = serializers.FloatField(help_text=_("内存碎片率"))


class RedisPersistenceInfoSerializer(serializers.Serializer):
    """Redis持久化信息"""

    loading = serializers.IntegerField(help_text=_("是否正在加载数据（0/1）"))
    rdb_changes_since_last_save = serializers.IntegerField(help_text=_("上次保存后的变更数"))
    rdb_bgsave_in_progress = serializers.IntegerField(help_text=_("是否正在进行RDB保存（0/1）"))
    rdb_last_save_time = serializers.IntegerField(help_text=_("上次RDB保存时间戳"))
    rdb_last_bgsave_status = serializers.CharField(help_text=_("上次RDB保存状态"))
    rdb_last_bgsave_time_sec = serializers.IntegerField(help_text=_("上次RDB保存耗时（秒）"))
    rdb_current_bgsave_time_sec = serializers.IntegerField(help_text=_("当前RDB保存耗时（秒）"))
    aof_enabled = serializers.IntegerField(help_text=_("是否启用AOF（0/1）"))
    aof_rewrite_in_progress = serializers.IntegerField(help_text=_("是否正在进行AOF重写（0/1）"))
    aof_rewrite_scheduled = serializers.IntegerField(help_text=_("是否计划AOF重写（0/1）"))
    aof_last_rewrite_time_sec = serializers.IntegerField(help_text=_("上次AOF重写耗时（秒）"))
    aof_current_rewrite_time_sec = serializers.IntegerField(help_text=_("当前AOF重写耗时（秒）"))
    aof_last_bgrewrite_status = serializers.CharField(help_text=_("上次AOF重写状态"))


class RedisStatsInfoSerializer(serializers.Serializer):
    """Redis统计信息"""

    total_connections_received = serializers.IntegerField(help_text=_("总连接数"))
    total_commands_processed = serializers.IntegerField(help_text=_("总命令处理数"))
    instantaneous_ops_per_sec = serializers.IntegerField(help_text=_("每秒操作数"))
    total_net_input_bytes = serializers.IntegerField(help_text=_("总输入字节数"))
    total_net_output_bytes = serializers.IntegerField(help_text=_("总输出字节数"))
    instantaneous_input_kbps = serializers.FloatField(help_text=_("瞬时输入速率（KB/s）"))
    instantaneous_output_kbps = serializers.FloatField(help_text=_("瞬时输出速率（KB/s）"))
    rejected_connections = serializers.IntegerField(help_text=_("拒绝的连接数"))
    sync_full = serializers.IntegerField(help_text=_("全量同步次数"))
    sync_partial_ok = serializers.IntegerField(help_text=_("部分同步成功次数"))
    sync_partial_err = serializers.IntegerField(help_text=_("部分同步失败次数"))
    expired_keys = serializers.IntegerField(help_text=_("过期的键数量"))
    evicted_keys = serializers.IntegerField(help_text=_("淘汰的键数量"))
    keyspace_hits = serializers.IntegerField(help_text=_("键空间命中次数"))
    keyspace_misses = serializers.IntegerField(help_text=_("键空间未命中次数"))
    pubsub_channels = serializers.IntegerField(help_text=_("发布订阅频道数"))
    pubsub_patterns = serializers.IntegerField(help_text=_("发布订阅模式数"))


class RedisSlavesSerializer(serializers.Serializer):
    slave_index = serializers.CharField(required=False, help_text=_("从节点编号"))
    ip = serializers.CharField(required=False, help_text=_("从节点IP"))
    port = serializers.IntegerField(required=False, help_text=_("从节点端口"))
    state = serializers.CharField(required=False, help_text=_("状态"))
    offset = serializers.IntegerField(required=False, help_text=_("复制偏移量"))
    seq = serializers.IntegerField(required=False, help_text=_("序列号"))


class RedisReplicationInfoSerializer(serializers.Serializer):
    """Redis复制信息"""

    role = serializers.CharField(help_text=_("角色（master/slave）"))
    connected_slaves = serializers.IntegerField(help_text=_("已连接的从节点数量"))
    master_replid = serializers.CharField(required=False, help_text=_("主节点复制ID"))
    master_replid2 = serializers.CharField(required=False, help_text=_("主节点复制ID2"))
    master_repl_offset = serializers.IntegerField(help_text=_("主节点复制偏移量"))
    second_repl_offset = serializers.IntegerField(required=False, help_text=_("第二复制偏移量"))
    repl_backlog_active = serializers.IntegerField(help_text=_("复制积压缓冲区是否激活（0/1）"))
    repl_backlog_size = serializers.IntegerField(help_text=_("复制积压缓冲区大小"))
    repl_backlog_first_byte_offset = serializers.IntegerField(help_text=_("复制积压缓冲区首字节偏移量"))
    repl_backlog_histlen = serializers.IntegerField(help_text=_("复制积压缓冲区历史长度"))
    slaves = serializers.ListSerializer(child=RedisSlavesSerializer(), help_text=_("从节点信息"))
    # 从节点特有字段
    master_host = serializers.CharField(required=False, help_text=_("主节点主机"))
    master_port = serializers.IntegerField(required=False, help_text=_("主节点端口"))
    master_link_status = serializers.CharField(required=False, help_text=_("主节点连接状态"))
    master_last_io_seconds_ago = serializers.IntegerField(required=False, help_text=_("主节点最后IO时间（秒前）"))
    master_sync_in_progress = serializers.IntegerField(required=False, help_text=_("是否正在同步（0/1）"))


class RedisCPUInfoSerializer(serializers.Serializer):
    """Redis CPU使用信息"""

    used_cpu_sys = serializers.FloatField(help_text=_("系统CPU使用时间"))
    used_cpu_user = serializers.FloatField(help_text=_("用户CPU使用时间"))
    used_cpu_sys_children = serializers.FloatField(help_text=_("子进程系统CPU使用时间"))
    used_cpu_user_children = serializers.FloatField(help_text=_("子进程用户CPU使用时间"))


class RedisKeyspaceInfoSerializer(serializers.Serializer):
    """Redis键空间信息"""

    db_index = serializers.IntegerField(help_text=_("数据库索引"))
    keys = serializers.IntegerField(help_text=_("键数量"))
    expires = serializers.IntegerField(help_text=_("设置了过期时间的键数量"))
    avg_ttl = serializers.IntegerField(help_text=_("平均TTL（毫秒）"))
