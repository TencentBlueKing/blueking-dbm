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

import type { PermissionRule, PermissionRuleAccount, PermissionRuleInfo } from '@services/types';

import { isRecentDays } from '@utils';

export default class MongodbPermissonAccount implements PermissionRule {
  account: PermissionRuleAccount;
  permission: {
    mongodb_account_delete: boolean;
    mongodb_add_account_rule: boolean;
  };
  rules: PermissionRuleInfo[];

  constructor(payload = {} as MongodbPermissonAccount) {
    this.account = payload.account;
    this.permission = payload.permission;
    this.rules = payload.rules;
  }

  get isNew() {
    return isRecentDays(this.account.create_time, 24 * 3);
  }
}
