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

import { bytePretty, isRecentDays, utcDisplayTime } from '@utils';

import { t } from '@locales/index';

export default class DorisNode {
  static ROLE_FOLLOWER = 'doris_follower';
  static ROLE_OBSERVER = 'doris_observer';
  static ROLE_HOT = 'doris_backend_hot';
  static ROLE_COLD = 'doris_backend_cold';

  static roleLabelMap = {
    [DorisNode.ROLE_FOLLOWER]: t('Follower节点'),
    [DorisNode.ROLE_OBSERVER]: t('Observer节点'),
    [DorisNode.ROLE_HOT]: t('热节点'),
    [DorisNode.ROLE_COLD]: t('冷节点'),
  };

  bk_cloud_id: number;
  bk_cloud_name: string;
  bk_host_id: number;
  bk_host_name: string;
  cpu: number;
  create_at: string;
  disk: number;
  ip: string;
  machine_type: string;
  mem: number;
  node_count: number;
  role: string;
  status: number;
  permission: Record<
    | 'doris_access_entry_view'
    | 'doris_destroy'
    | 'doris_enable_disable'
    | 'doris_reboot'
    | 'doris_replace'
    | 'doris_scale_up'
    | 'doris_shrink'
    | 'doris_view',
    boolean
  >;

  constructor(payload = {} as DorisNode) {
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.bk_host_id = payload.bk_host_id;
    this.bk_host_name = payload.bk_host_name;
    this.cpu = payload.cpu || 0;
    this.create_at = payload.create_at;
    this.disk = payload.disk || 0;
    this.ip = payload.ip;
    this.machine_type = payload.machine_type;
    this.mem = payload.mem || 0;
    this.node_count = payload.node_count || 0;
    this.role = payload.role;
    this.status = payload.status || 0;
    this.permission = payload.permission || {};
  }

  get isNew() {
    return isRecentDays(this.create_at, 24);
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }

  get isFollower() {
    return this.role === DorisNode.ROLE_FOLLOWER;
  }

  get isObserver() {
    return this.role === DorisNode.ROLE_OBSERVER;
  }

  get isHot() {
    return this.role === DorisNode.ROLE_HOT;
  }

  get isCold() {
    return this.role === DorisNode.ROLE_COLD;
  }

  get isAbnormal() {
    return this.status === 0;
  }

  get memText() {
    return bytePretty(this.mem * 1024 * 1024);
  }

  get roleLabel() {
    return DorisNode.roleLabelMap[this.role];
  }
}
