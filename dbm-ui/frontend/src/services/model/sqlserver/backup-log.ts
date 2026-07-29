/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */

export interface SqlserverBackupLogRecord {
  backup_begin_time?: string;
  backup_end_time?: string;
  backup_file_tag?: string;
  backup_host?: string;
  backup_id: string;
  backup_port?: number;
  backup_task_end_time?: string;
  backup_task_start_time?: string;
  backup_type: string;
  bill_id: string;
  bk_biz_id?: number;
  bk_cloud_id?: number;
  charset?: string;
  checkpoint_lsn?: string;
  cluster_domain?: string;
  cluster_id?: number;
  cluster_type?: string;
  compatibility_level?: number;
  created_at?: string | null;
  data_schema_grant?: string;
  database_backup_lsn?: string;
  db_list?: string;
  db_size_kb?: number;
  dbname?: string;
  file_cnt?: number;
  file_name?: string;
  file_size_kb: number;
  first_lsn?: string;
  id?: number;
  is_full_backup?: boolean;
  last_lsn?: string;
  local_path?: string;
  master_ip?: string;
  master_port?: number;
  role: string;
  task_id?: string;
  time_zone?: string;
  updated_at?: string | null;
  version?: string;
}

export default class SqlserverBackupLog {
  backup_db_list: string[];
  backup_db_size_kb: number;
  backup_file_size_kb: number;
  backup_id: string;
  bill_id: string;
  complete: boolean;
  end_time: string;
  excluded_db_list: string[];
  expected_cnt: number;
  logs: SqlserverBackupLogRecord[];
  real_cnt: number;
  role: string;
  start_time: string;

  constructor(payload = {} as SqlserverBackupLog) {
    this.backup_id = payload.backup_id || '';
    this.complete = payload.complete || false;
    this.end_time = payload.end_time || '';
    this.expected_cnt = payload.expected_cnt || 0;
    this.logs = payload.logs || [];
    this.real_cnt = payload.real_cnt || 0;
    this.role = payload.role || '';
    this.start_time = payload.start_time || '';
    this.backup_db_list = payload.backup_db_list || [];
    this.backup_db_size_kb = payload.backup_db_size_kb || 0;
    this.backup_file_size_kb = payload.backup_file_size_kb || 0;
    this.excluded_db_list = payload.excluded_db_list || [];
    this.bill_id = payload.bill_id || '';
  }
}
