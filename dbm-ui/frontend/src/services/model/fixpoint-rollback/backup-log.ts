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

export default class BackupLog {
  backup_id: string;
  backup_time: string;
  backup_type: string;
  master_host: string;
  master_port: number;
  mysql_host: string;
  mysql_port: number;
  mysql_role: string;
  task_id: string;

  constructor(payload = {} as BackupLog) {
    this.backup_id = payload.backup_id;
    this.backup_time = payload.backup_time;
    this.backup_type = payload.backup_type;
    this.master_host = payload.master_host;
    this.master_port = payload.master_port;
    this.mysql_host = payload.mysql_host;
    this.mysql_port = payload.mysql_port;
    this.mysql_role = payload.mysql_role;
    this.task_id = payload.task_id;
  }
}
