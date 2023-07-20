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
import { RedisClusterTypes } from '@services/model/redis/redis';
import RedisClusterNodeByIpModel from '@services/model/redis/redis-cluster-node-by-ip';

interface CommonNode {
  id: number;
  machine__ip: string;
  machine__spec_config: RedisClusterNodeByIpModel['spec_config'];
  name: string;
  port: number;
  status: string;
  version: string;
}

interface StorageNode extends CommonNode {
  instance_role: string
}

export default class RedisClusterNodeByFilter {
  cluster: {
    bk_cloud_id: number;
    cluster_type: RedisClusterTypes;
    deploy_plan: any;
    deploy_plan_id: number;
    id: number;
    immute_domain: string;
    major_version: string;
    name: string;
    proxy_count: number;
    redis_master_count: number;
    redis_slave_count: number;
    region: string;
    capacity: {
      used: string,
      total: string
    }
  };
  proxy: CommonNode[];
  storage: StorageNode[];
  constructor(payload = {} as RedisClusterNodeByFilter) {
    this.cluster = payload.cluster;
    this.proxy = payload.proxy;
    this.storage = payload.storage;
  }
}
