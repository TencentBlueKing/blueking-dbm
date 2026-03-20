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
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType, InstanceRole, MachineType, TenDBClusterSpiderRole
from blue_krill.data_types.enum import EnumField, StrStructuredEnum

mysql_cluster_type_choices = [
    (ClusterType.TenDBSingle.value, ClusterType.TenDBSingle.name),
    (ClusterType.TenDBHA.value, ClusterType.TenDBHA.name),
    (ClusterType.TenDBCluster.value, ClusterType.TenDBCluster.name),
]

mysql_machine_type_choices = [
    (MachineType.SINGLE.value, MachineType.SINGLE.name),
    (MachineType.BACKEND.value, MachineType.BACKEND.name),
    (MachineType.REMOTE.value, MachineType.REMOTE.name),
    (MachineType.SPIDER.value, MachineType.SPIDER.name),
]

mysql_instance_role_choices = [
    (InstanceRole.BACKEND_MASTER.value, InstanceRole.BACKEND_MASTER.name),
    (InstanceRole.BACKEND_SLAVE.value, InstanceRole.BACKEND_SLAVE.name),
    (InstanceRole.REMOTE_MASTER.value, InstanceRole.REMOTE_MASTER.name),
    (InstanceRole.REMOTE_SLAVE.value, InstanceRole.REMOTE_SLAVE.name),
    (TenDBClusterSpiderRole.SPIDER_MASTER, TenDBClusterSpiderRole.SPIDER_MASTER.name),
]

mysql_popular_runtime_variables = [
    "bind_address",
    "binlog_cache_size",
    "binlog_checksum",
    "binlog_expire_logs_auto_purge",
    "binlog_expire_logs_seconds",
    "binlog_format",
    "binlog_group_commit_sync_delay",
    "binlog_group_commit_sync_no_delay_count",
    "binlog_gtid_simple_recovery",
    "binlog_max_flush_queue_time",
    "binlog_order_commits",
    "binlog_row_event_max_size",
    "binlog_row_image",
    "binlog_row_metadata",
    "binlog_row_value_options",
    "binlog_rows_query_log_events",
    "binlog_stmt_cache_size",
    "character_set_client",
    "character_set_client_handshake",
    "character_set_connection",
    "character_set_database",
    "character_set_filesystem",
    "character_set_results",
    "character_set_server",
    "character_set_system",
    "collation_connection",
    "collation_database",
    "collation_server",
    "connect_timeout",
    "connection_memory_chunk_size",
    "connection_memory_limit",
    "default_collation_for_utf8mb4",
    "default_storage_engine",
    "general_log",
    "general_log_file",
    "gtid_executed",
    "gtid_executed_compression_period",
    "gtid_mode",
    "gtid_next",
    "gtid_owned",
    "gtid_purged",
    "gtid_undeleted",
    "innodb_adaptive_hash_index",
    "innodb_adaptive_hash_index_parts",
    "innodb_buffer_pool_chunk_size",
    "innodb_buffer_pool_instances",
    "innodb_buffer_pool_size",
    "innodb_commit_concurrency",
    "innodb_ddl_buffer_size",
    "innodb_ddl_threads",
    "innodb_deadlock_detect",
    "innodb_dedicated_server",
    "innodb_default_row_format",
    "innodb_fast_ddl",
    "innodb_fast_shutdown",
    "innodb_file_per_table",
    "innodb_force_recovery",
    "innodb_io_capacity",
    "innodb_log_file_size",
    "innodb_log_files_in_group",
    "innodb_open_files",
    "innodb_parallel_ddl",
    "innodb_parallel_read_threads",
    "innodb_read_io_threads",
    "innodb_strict_mode",
    "innodb_write_io_threads",
    "interactive_timeout",
    "join_buffer_size",
    "key_buffer_size",
    "key_cache_age_threshold",
    "key_cache_block_size",
    "key_cache_division_limit",
    "large_files_support",
    "large_page_size",
    "large_pages",
    "last_insert_id",
    "local_infile",
    "lock_wait_timeout",
    "locked_in_memory",
    "log_bin",
    "log_queries_not_using_indexes",
    "log_raw",
    "log_replica_updates",
    "log_slave_updates",
    "log_slow_admin_statements",
    "log_slow_extra",
    "log_slow_replica_statements",
    "log_slow_slave_statements",
    "log_statement_of_query_event",
    "log_statements_unsafe_for_binlog",
    "log_throttle_queries_not_using_indexes",
    "log_timestamps",
    "long_query_time",
    "low_priority_updates",
    "lower_case_file_system",
    "lower_case_table_names",
    "max_allowed_packet",
    "max_binlog_cache_size",
    "max_binlog_size",
    "max_binlog_stmt_cache_size",
    "max_connect_errors",
    "max_connections",
    "max_join_size",
    "max_length_for_sort_data",
    "max_prepared_stmt_count",
    "net_buffer_length",
    "net_read_timeout",
    "net_retry_count",
    "net_write_timeout",
    "open_files_limit",
    "performance_schema",
    "port",
    "query_alloc_block_size",
    "query_prealloc_size",
    "read_buffer_size",
    "read_only",
    "replica_allow_batching",
    "replica_checkpoint_group",
    "replica_checkpoint_period",
    "replica_compressed_protocol",
    "replica_exec_mode",
    "replica_max_allowed_packet",
    "replica_net_timeout",
    "replica_parallel_type",
    "replica_parallel_workers",
    "replica_pending_jobs_size_max",
    "replica_preserve_commit_order",
    "replica_skip_errors",
    "replica_sql_verify_checksum",
    "replica_transaction_retries",
    "replica_type_conversions",
    "replication_optimize_for_static_plugin_config",
    "replication_sender_observe_commit_only",
    "schema_definition_cache",
    "skip_external_locking",
    "skip_name_resolve",
    "skip_networking",
    "skip_replica_start",
    "skip_show_database",
    "skip_slave_start",
    "slave_allow_batching",
    "slave_checkpoint_group",
    "slave_checkpoint_period",
    "slave_compressed_protocol",
    "slave_exec_mode",
    "slave_max_allowed_packet",
    "slave_net_timeout",
    "slave_parallel_type",
    "slave_parallel_workers",
    "slave_pending_jobs_size_max",
    "slave_preserve_commit_order",
    "slave_rows_search_algorithms",
    "slave_skip_errors",
    "slave_sql_verify_checksum",
    "slave_transaction_retries",
    "slave_type_conversions",
    "slow_launch_time",
    "slow_query_log",
    "slow_query_log_file",
    "sort_buffer_size",
    "sql_big_selects",
    "sql_buffer_result",
    "sql_generate_invisible_primary_key",
    "sql_log_bin",
    "sql_log_off",
    "sql_mode",
    "sql_notes",
    "sql_quote_show_create",
    "sql_replica_skip_counter",
    "sql_require_primary_key",
    "sql_safe_updates",
    "sql_select_limit",
    "sql_slave_skip_counter",
    "sql_warnings",
    "sync_binlog",
    "table_definition_cache",
    "table_open_cache",
    "table_open_cache_instances",
    "tablespace_definition_cache",
    "thread_cache_size",
    "thread_handling",
    "thread_handling_switch_mode",
    "thread_pool_high_prio_mode",
    "thread_pool_high_prio_tickets",
    "thread_pool_idle_timeout",
    "thread_pool_max_threads",
    "thread_pool_oversubscribe",
    "thread_pool_size",
    "thread_pool_stall_limit",
    "thread_stack",
    "transaction_isolation",
    "tx_isolation",
    "unique_checks",
    "updatable_views_with_limit",
    "version",
    "wait_timeout",
    "warning_count",
]

mysql_popular_runtime_status = [
    "Uptime",
    "Open_tables",
    "Aborted_clients",
    "Aborted_connects",
    "Queries",
    "Questions",
    "Slow_queries",
    "Table_open_cache_misses",
    "Table_open_cache_hits",
    "Threads_connected",
    "Threads_running",
]

mysql_slave_status_masks = [
    "Master_User",
    "Master_SSL_Allowed",
    "Master_SSL_CA_File",
    "Master_SSL_CA_Path",
    "Master_SSL_Cert",
    "Master_SSL_Cipher",
    "Master_SSL_Key",
    "Master_TLS_Version",
    "Relay_Log_Space",
    "Master_SSL_Verify_Server_Cert",
    "Master_UUID",
    "Master_Info_File",
    "Master_Retry_Count",
    "Master_Bind",
    "Master_SSL_Crl",
    "Master_SSL_Crlpath",
    "Connect_Retry",
    "Replicate_Ignore_Server_Ids",
    "Last_IO_Error_Timestamp",
    "Last_SQL_Error_Timestamp",
    "Until_Condition",
    "Until_Log_File",
    "Until_Log_Pos",
    "Skip_Counter",
    "Channel_Name",
]

mysql_metric_name_choices = [
    ("cpu_summary", _("cpu 负载")),
    ("qps_summary", _("qps 请求量")),
    ("slow_count", _("slowlog 慢日志数量")),
    ("threads_running", _("threads 线程数 趋势")),
    ("connections", _("连接数 趋势")),
]


class MySQLProcessListInstanceGroupType(StrStructuredEnum):
    MasterGroup = EnumField("master_group", _("主分组"))
    SlaveGroup = EnumField("slave_group", _("从分组"))


class MySQLProcessListFilterFieldType(StrStructuredEnum):
    AccessSourceAddress = EnumField("access_source_address", _("访问来源地址"))
    ProxyAddress = EnumField("proxy_address", _("接入层地址"))
    StorageAddress = EnumField("mysql_address", _("存储层地址"))
    Command = EnumField("command", _("正在执行的命令操作"))
    User = EnumField("user", _("访问账号"))
    DB = EnumField("db", _("访问 DB 名"))
    State = EnumField("state", _("连接状态"))
    Time = EnumField("time", _("连接持续时长, 单位是秒"))


class MySQLProcessListFilterOpType(StrStructuredEnum):
    OpIn = EnumField("in", _("包含, 是, 存在"))
    OpNotIn = EnumField("not in", _("不包含, 不是, 不存在"))
    OpGt = EnumField(">", _("大于"))
    OpLt = EnumField("<", _("小于"))
    OpGte = EnumField(">=", _("大于等于"))
    OpLte = EnumField("<=", _("小于等于"))


mysql_slowlog_metric_name_choices = [
    ("query_time", _("按查询执行时间排序聚合")),
    ("slow_count", _("按照慢查询数量排序聚合")),
    ("rows_scan", _("按照查询扫描行数排序聚合")),
]

processlist_group_by_choices = [
    ("group_by_fingerprint", _("按 sql 类型聚合计数")),
    ("longest_top_5", _("按连 sql 执行时长排序前 5")),
    ("group_by_user", _("按连接账号名聚合计数")),
    ("group_by_client_host", _("按访问来源ip聚合计数")),
]

mysql_config_update_allowed = [
    ("backup", _("备份配置")),
    ("mysql_monitor", _("监控配置")),
    ("checksum", _("校验配置")),
]
