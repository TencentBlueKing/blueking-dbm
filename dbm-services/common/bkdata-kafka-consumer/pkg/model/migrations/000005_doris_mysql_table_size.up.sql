CREATE TABLE `mysql_db_table_size` (
   `cluster_domain` varchar(200) NOT NULL,
   `dteventtimehour` datetime NOT NULL COMMENT 'datetime precision to hour, used as where,group-by,expire',
   `report_time` varchar(32) NULL,
   `thedate` int NOT NULL,
   `dteventtimestamp` bigint NOT NULL,
   `instance_host` varchar(60) NULL,
   `instance_port` int NULL,
   `shard_value` int NULL,
   `database_name` varchar(100) NULL,
   `table_name` varchar(100) NULL,
   `table_size` bigint NULL,
   `original_database_name` varchar(100) NULL,
   `database_size` bigint NULL,
   `machine_type` varchar(60) NULL,
   `instance_role` varchar(60) NULL,
   `bk_biz_id` int NULL,
   `bk_cloud_id` int NULL
) ENGINE=OLAP
DUPLICATE KEY(`cluster_domain`,`dteventtimehour`)
PARTITION BY RANGE(`dteventtimehour`)()
DISTRIBUTED BY HASH(`cluster_domain`) BUCKETS 12
PROPERTIES (
    "replication_allocation" = "tag.location.default: 1",
    "min_load_replica_num" = "-1",
    "bloom_filter_columns" = "cluster_domain, database_name, bk_biz_id, table_name",
    "is_being_synced" = "false",
    "dynamic_partition.enable" = "true",
    "dynamic_partition.time_unit" = "DAY",
    "dynamic_partition.time_zone" = "Asia/Shanghai",
    "dynamic_partition.start" = "-30",
    "dynamic_partition.end" = "2",
    "dynamic_partition.prefix" = "p",
    "dynamic_partition.replication_allocation" = "tag.location.default: 1",
    "dynamic_partition.buckets" = "12",
    "dynamic_partition.create_history_partition" = "true",
    "dynamic_partition.history_partition_num" = "7",
    "dynamic_partition.hot_partition_num" = "0",
    "dynamic_partition.reserved_history_periods" = "NULL",
    "dynamic_partition.storage_policy" = "",
    "storage_medium" = "ssd",
    "storage_format" = "V2",
    "inverted_index_storage_format" = "V2",
    "light_schema_change" = "true",
    "disable_auto_compaction" = "false",
    "enable_single_replica_compaction" = "false",
    "group_commit_interval_ms" = "10000",
    "group_commit_data_bytes" = "134217728"
);
-- "replication_num" = "1"
-- sessionVariables=group_commit=async_mode
-- ALTER TABLE mysql_db_table_size SET ("group_commit_interval_ms"="30000");
--     "timeout" = "60",
--     "max_filter_ratio"="0.2"