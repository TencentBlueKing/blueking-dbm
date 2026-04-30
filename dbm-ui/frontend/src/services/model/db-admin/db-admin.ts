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

export default class DBAdmin {
  bk_biz_id: number;
  db_type: string;
  db_type_display: string;
  is_show: boolean;
  permission: {
    db_manage: boolean;
    dba_admin_edit: boolean;
    global_dba_admin_edit: boolean;
  };
  update_at: string;
  updater: string;
  users: string[];

  constructor(payload = {} as DBAdmin) {
    this.bk_biz_id = payload.bk_biz_id;
    this.db_type = payload.db_type;
    this.db_type_display = payload.db_type_display;
    this.is_show = payload.is_show;
    this.permission = payload.permission || {};
    this.update_at = payload.update_at;
    this.updater = payload.updater;
    this.users = payload.users;
  }
}
