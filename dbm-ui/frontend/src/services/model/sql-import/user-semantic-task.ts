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

export default class UserSemanticTasks {
  bk_biz_id: number;
  cluster_type: string;
  created_at: string;
  is_alter: boolean;
  root_id: string;
  status: string;

  constructor(payload = {} as UserSemanticTasks) {
    this.bk_biz_id = payload.bk_biz_id;
    this.cluster_type = payload.cluster_type;
    this.created_at = payload.created_at;
    this.is_alter = payload.is_alter;
    this.status = payload.status;
    this.root_id = payload.root_id;
  }

  get isFailed() {
    return !this.isSucceeded && !this.isPending;
  }

  get isPending() {
    return ['CREATED', 'RUNNING'].includes(this.status);
  }

  get isSucceeded() {
    return this.status === 'FINISHED';
  }
}
