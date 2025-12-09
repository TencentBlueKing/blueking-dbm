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

export default class MysqlMergeDiskSpace {
  source: string;
  target: string;
  target_cluster_type: string;
  db_list: string[];
  clone_db_list: string[];
  ignore_db_list: string[];
  data_schema_grant: string;
  db_size: Record<string, number>;
  same_target_sum_size: number;
  same_target_index: number[];
  disk_size: {
    used: number;
    total: number;
    mount_point: string;
    host: string;
    used_percent: string;
    used_percent_future: string;
  };
  suggestion: string;

  constructor(payload = {} as MysqlMergeDiskSpace) {
    this.source = payload.source;
    this.target = payload.target;
    this.target_cluster_type = payload.target_cluster_type;
    this.db_list = payload.db_list;
    this.clone_db_list = payload.clone_db_list;
    this.ignore_db_list = payload.ignore_db_list;
    this.data_schema_grant = payload.data_schema_grant;
    this.db_size = payload.db_size;
    this.same_target_sum_size = payload.same_target_sum_size;
    this.same_target_index = payload.same_target_index;
    this.disk_size = payload.disk_size;
    this.suggestion = payload.suggestion;
  }
}
