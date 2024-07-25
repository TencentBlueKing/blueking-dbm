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

export default class AdminPassword {
  bk_cloud_id: number;
  bk_cloud_name: string;
  component: string;
  ip: string;
  lock_until: string;
  operator: string;
  password: string;
  port: number;
  update_time: string;
  username: string;

  constructor(payload = {} as AdminPassword) {
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.component = payload.component;
    this.ip = payload.ip;
    this.lock_until = payload.lock_until;
    this.operator = payload.operator;
    this.password = payload.password;
    this.port = payload.port;
    this.update_time = payload.update_time;
    this.username = payload.username;
  }

  get uniqueKey() {
    return `${this.bk_cloud_id}:${this.ip}:${this.port}`;
  }

  get lockUntilDisplay() {
    return dayjs(this.lock_until).format('YYYY-MM-DD HH:mm:ss');
  }

  get updateTimeDisplay() {
    return dayjs(this.update_time).format('YYYY-MM-DD HH:mm:ss');
  }
}
