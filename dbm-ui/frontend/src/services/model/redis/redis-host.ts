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

import RedisClusterNodeByIpModel from '@services/model/redis/redis-cluster-node-by-ip';
import type { HostDetails } from '@services/source/ipchooser';

import { switchToNormalRole } from '@utils';
export default class RedisHost {
  bk_cloud_id: number;
  bk_host_id: number;
  cluster_id: number;
  host_info: HostDetails;
  ip: string;
  instance_count: number;
  role: string;
  running_slave: number;
  running_master: number;
  spec_config: RedisClusterNodeByIpModel['spec_config'];
  total_master: number;
  total_slave: number;
  unavailable_master: number;
  unavailable_slave: number;
  isShowTip: boolean;
  master_domain?: string;
  constructor(payload = {} as RedisHost) {
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_host_id = payload.bk_host_id;
    this.role = switchToNormalRole(payload.role);
    this.cluster_id = payload.cluster_id;
    this.host_info = payload.host_info;
    this.ip = payload.ip;
    this.instance_count = payload.instance_count;
    this.running_slave = payload.running_slave;
    this.running_master = payload.running_master;
    this.spec_config = payload.spec_config;
    this.master_domain = payload.master_domain;
    this.total_master = payload.total_master;
    this.total_slave = payload.total_slave;
    this.unavailable_master = payload.unavailable_master;
    this.unavailable_slave = payload.unavailable_slave;
    this.isShowTip = false;
  }

  get isMasterFailover() {
    return this.role === 'master' && this.unavailable_master > 0;
  }

  get isSlaveFailover() {
    return this.role === 'master' && this.unavailable_slave > 0;
  }

  get isMaster() {
    return this.role === 'master';
  }
}
