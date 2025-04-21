// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysql_table_size

var CREATE_TABLE_SQL_MYSQL = `
CREATE TABLE IF NOT EXISTS mysql_db_table_size (
  id bigint NOT NULL AUTO_INCREMENT,
  cluster_domain varchar(200) NOT NULL,
  dteventtimehour datetime NOT NULL COMMENT 'datetime precision to hour, used as where,group-by,expire',
  report_time varchar(32) DEFAULT NULL,
  thedate int NOT NULL,
  dteventtimestamp bigint NOT NULL,
  instance_host varchar(60) DEFAULT NULL,
  instance_port int DEFAULT NULL,
  shard_value int DEFAULT NULL,
  database_name varchar(100) DEFAULT NULL,
  table_name varchar(100) DEFAULT NULL,
  table_size bigint DEFAULT NULL,
  original_database_name varchar(100) DEFAULT NULL,
  database_size bigint DEFAULT NULL,
  machine_type varchar(60) DEFAULT NULL,
  instance_role varchar(60) DEFAULT NULL,
  bk_biz_id int DEFAULT NULL,
  bk_cloud_id int DEFAULT NULL,
  PRIMARY KEY (cluster_domain,dteventtimehour,id),
  KEY idx_0 (id),
  KEY idx_1 (cluster_domain,database_name,original_database_name,table_name,dteventtimehour),
  KEY idx_2 (cluster_domain,dteventtimehour),
  KEY idx_3 (dteventtimehour,cluster_domain,database_name),
  KEY idx_4 (dteventtimehour),
  KEY idx_5 (instance_host,instance_port)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 

`

var CREATE_TABLE_SQL_DORIS = `
CREATE TABLE IF NOT EXISTS mysql_db_table_size (
  cluster_domain varchar(200) NOT NULL,
  dteventtimehour datetime NOT NULL COMMENT "datetime precision to hour, used as where,group-by,expire",
  report_time varchar(32) NULL,
  thedate int NOT NULL,
  dteventtimestamp bigint NOT NULL,
  instance_host varchar(60) NULL,
  instance_port int NULL,
  shard_value int NULL,
  database_name varchar(100) NULL,
  table_name varchar(100) NULL,
  table_size bigint NULL,
  original_database_name varchar(100) NULL,
  database_size bigint NULL,
  machine_type varchar(60) NULL,
  instance_role varchar(60) NULL,
  bk_biz_id int NULL,
  bk_cloud_id int NULL
) ENGINE=OLAP
DUPLICATE KEY(cluster_domain, dteventtimehour)
PARTITION BY RANGE(dteventtimehour)()
DISTRIBUTED BY HASH(cluster_domain) BUCKETS 12
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
`
