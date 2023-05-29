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

export default class SemanticData {
  backup: Array<{
    db_patterns: string [],
    backup_on: string,
    table_patterns: string []
  }>;
  bk_biz_id: number;
  charset: string;
  cluster_ids: number[];
  created_by: string;
  execute_db_infos: Array<{
    dbnames: string[];
    ignore_dbnames: string[];
  }>;
  execute_objects: Array<{
    dbnames: string[];
    ignore_dbnames: string[];
    sql_file: string;
  }>;
  execute_sql_files: string[];
  import_mode: string;
  path: string;
  ticket_mode: {
    mode: string;
    trigger_time: string
  };
  ticket_type: string;

  constructor(payload = {} as SemanticData) {
    this.backup = payload.backup;
    this.bk_biz_id = payload.bk_biz_id;
    this.charset = payload.charset;
    this.cluster_ids = payload.cluster_ids;
    this.created_by = payload.created_by;
    this.execute_db_infos = payload.execute_db_infos;
    this.execute_objects = payload.execute_objects;
    this.execute_sql_files = payload.execute_sql_files;
    this.import_mode = payload.import_mode;
    this.path = payload.path;
    this.ticket_mode = payload.ticket_mode;
    this.ticket_type = payload.ticket_type;
  }
}
