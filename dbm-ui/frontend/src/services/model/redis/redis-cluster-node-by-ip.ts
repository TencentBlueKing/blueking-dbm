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

export default class RedisClusterNodeByIp {
  bk_host_id: number;
  bk_cloud_id: number;
  cluster: {
    bk_cloud_id: number;
    cluster_type: string;
    deploy_plan: {
      capacity: string;
      cluster_type: string;
      id: number;
      machine_pair_cnt: number;
      name: string;
      shard_cnt: number;
    },
    deploy_plan_id: number;
    immute_domain: string;
    id: number;
    name: string;
    proxy_count: number;
    redis_master_count: number;
    redis_slave_count: number;
    region: string;
  };
  ip: string;
  role: string;
  running_master: number;
  running_slave: number;
  spec_id: number;
  spec_config: {
    count: number;
    cpu: {
      max: number;
      min: number;
    },
    id: number;
    mem: {
      max: number;
      min: number;
    },
    name: string;
    qps: {
      max: number;
      min: number;
    },
    storage_spec: {
      mount_point: string;
      size: number;
      type: string;
    }[],
  };

  constructor(payload = {} as RedisClusterNodeByIp) {
    this.bk_host_id = payload.bk_host_id;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.cluster = payload.cluster;
    this.ip = payload.ip;
    this.role = payload.role;
    this.running_master = payload.running_master;
    this.running_slave = payload.running_slave;
    this.spec_id = payload.spec_id;
    this.spec_config = payload.spec_config;
  }
}
