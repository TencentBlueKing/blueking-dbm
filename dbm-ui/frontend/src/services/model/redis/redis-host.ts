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
import RedisClusterNodeByIpModel from '@/services/model/redis/redis-cluster-node-by-ip';
import type { HostDetails } from '@/services/types/ip';

export default class RedisHost {
  bk_cloud_id: number;
  bk_host_id: number;
  cluster_id: number;
  host_info: HostDetails;
  ip: string;
  instance_count: number;
  role: string;
  spec_config: RedisClusterNodeByIpModel['spec'];
  master_domain?: string;
  constructor(payload = {} as RedisHost) {
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_host_id = payload.bk_host_id;
    this.role = payload.role;
    this.cluster_id = payload.cluster_id;
    this.host_info = payload.host_info;
    this.ip = payload.ip;
    this.instance_count = payload.instance_count;
    this.spec_config = payload.spec_config;
    this.master_domain = payload.master_domain;
  }
}
