// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysql_binlog_result

var CREATE_TABLE_SQL = `
CREATE TABLE IF NOT EXISTS tb_mysql_binlog_result (
  id bigint(20) NOT NULL AUTO_INCREMENT,
  bk_biz_id int(11) NOT NULL,
  cluster_id int(11) NOT NULL,
  cluster_domain varchar(120) DEFAULT '',
  db_role varchar(20) NOT NULL DEFAULT '',
  host varchar(64) NOT NULL,
  port int(11) DEFAULT '0',
  filename varchar(64) NOT NULL,
  filesize bigint(20) NOT NULL,
  file_mtime varchar(32) NOT NULL,
  start_time varchar(32) DEFAULT '',
  stop_time varchar(32) DEFAULT '',
  backup_status int(11) DEFAULT '-2',
  backup_status_info varchar(120) NOT NULL DEFAULT '',
  task_id varchar(64) DEFAULT '',
  file_retention_tag varchar(60) NOT NULL DEFAULT '',
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  is_deleted tinyint(4) NOT NULL DEFAULT '0',
  backup_enable tinyint(4) DEFAULT '-1',
  PRIMARY KEY (id),
  UNIQUE KEY uniq_1 (cluster_domain,host,port,filename),
  KEY idx1_ (bk_biz_id,file_mtime),
  KEY idx_2 (file_mtime),
  KEY idx_3 (host),
  KEY idx_4 (backup_status),
  KEY idx_5 (cluster_id),
  KEY idx_6 (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8

`
