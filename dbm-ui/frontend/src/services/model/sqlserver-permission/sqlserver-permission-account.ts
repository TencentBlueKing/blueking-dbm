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

import dayjs from 'dayjs';

import { utcDisplayTime } from '@utils';

export default class SqlserverPermissionAccount {
  account: {
    account_id: number;
    bk_biz_id: number;
    create_time: string;
    creator: string;
    password: string;
    user: string;
  };
  permission: {
    sqlserver_account_delete: boolean;
    sqlserver_add_account_rule: boolean;
  };
  rules: {
    access_db: string;
    account_id: number;
    bk_biz_id: number;
    create_time: string;
    creator: string;
    privilege: string;
    rule_id: number;
  }[];

  constructor(payload: SqlserverPermissionAccount) {
    this.account = payload.account;
    this.permission = payload.permission;
    this.rules = payload.rules;
  }

  get isNew() {
    return dayjs().isBefore(dayjs(this.account.create_time).add(24, 'hour'));
  }

  get createAtDisplay() {
    return utcDisplayTime(this.account.create_time);
  }
}
