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

export default class MongodbPermissonAccount {
  account: {
    account_id: number;
    bk_biz_id: number;
    create_time: string;
    creator: string;
    password: string;
    user: string;
  };
  rules: Array<{
    access_db: string;
    account_id: number;
    bk_biz_id: number;
    create_time: string;
    creator: string;
    privilege: string;
    rule_id: number;
  }>;

  constructor(payload = {} as MongodbPermissonAccount) {
    this.account = payload.account;
    this.rules = payload.rules;
  }

  get isNew() {
    const createTime = this.account.create_time;
    if (!createTime) {
      return false;
    }
    const createDay = dayjs(createTime);
    const today = dayjs();
    return today.diff(createDay, 'hour') <= 24;
  }
}
