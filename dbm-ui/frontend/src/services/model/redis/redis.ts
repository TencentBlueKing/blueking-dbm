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
import { PipelineStatus } from '@common/const';

import { isRecentDays } from '@utils';

export const enum RedisClusterTypes {
  PredixyTendisplusCluster = 'PredixyTendisplusCluster', // Tendisplus
  TwemproxyRedisInstance = 'TwemproxyRedisInstance', // TendisCache
  TwemproxyTendisSSDInstance = 'TwemproxyTendisSSDInstance', // TendisSSD
}

interface Node {
  name: string;
  ip: string;
  port: number;
  instance: string;
  status: string;
  phase: string;
  bk_instance_id: number;
  bk_host_id: number;
  bk_cloud_id: number;
  bk_biz_id: number;
  spec_config: {
    id: number;
    cpu: {
      max: number;
      min: number;
    },
    mem: {
      max: number;
      min: number;
    },
    qps: {
      max: number;
      min: number;
    },
    name: string;
    device_class: [],
    storage_spec:
    {
      size: number;
      type: string;
      mount_point: string;
    }[],
  }
}
export default class Redis {
  bk_biz_id: number;
  bk_biz_name: string;
  bk_cloud_id: number;
  bk_cloud_name: string;
  cluster_alias: string;
  cluster_capacity: number;
  cluster_entry: {
    cluster_entry_type: string;
    entry: string;
  }[];
  cluster_name: string;
  cluster_shard_num: number;
  cluster_spec: {
    creator: string;
    updater: string;
    spec_id: number;
    spec_name: string;
    spec_cluster_type: RedisClusterTypes;
    spec_machine_type: string;
    cpu: {
      max: number;
      min: number;
    },
    mem: {
      max: number;
      min: number;
    },
    device_class: [],
    storage_spec: [
      {
        size: number;
        type: string;
        mount_point: string;
      }
    ],
    desc: string;
    instance_num: number;
    qps: {
      max: number;
      min: number;
    }
  };
  cluster_stats: Record<string, any>;
  cluster_type: string;
  cluster_type_name: string;
  create_at: string;
  creator: string;
  dns_to_clb: boolean;
  id: number;
  machine_pair_cnt: number;
  major_version: string;
  master_domain: string;
  operations: {
    cluster_id: number;
    flow_id: number;
    operator: string;
    status: PipelineStatus;
    ticket_id: number;
    ticket_type: string;
    title: string;
  }[];
  permission: {
    redis_destroy: boolean;
    redis_keys_delete: boolean;
    redis_keys_extract: boolean;
    redis_open_close: boolean;
    redis_purge: boolean;
    redis_backup: boolean;
    redis_view: boolean;
    access_entry_edit: boolean;
  };
  phase: string;
  proxy: Node[];
  redis_master: Node[];
  redis_slave: Node[];
  region: string;
  status: string;
  update_at: string;
  updater: string;

  count: number;
  db_module_id: number;
  deploy_plan_id: number;
  cluster_time_zone: string;
  time_zone: string;

  constructor(payload = {} as Redis) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.cluster_name = payload.cluster_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.cluster_alias = payload.cluster_alias;
    this.db_module_id = payload.db_module_id;
    this.cluster_type = payload.cluster_type;
    this.cluster_type_name = payload.cluster_type_name;
    this.cluster_time_zone = payload.cluster_time_zone;
    this.time_zone = payload.time_zone;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.dns_to_clb = payload.dns_to_clb;
    this.id = payload.id;
    this.major_version = payload.major_version;
    this.deploy_plan_id = payload.deploy_plan_id;
    this.phase = payload.phase;
    this.region = payload.region;
    this.status = payload.status;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
    this.cluster_capacity = payload.cluster_capacity;
    this.operations = payload.operations;
    this.cluster_spec = payload.cluster_spec;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.master_domain = payload.master_domain;
    this.cluster_entry = payload.cluster_entry || [];
    this.permission = payload.permission || {};
    this.proxy = payload.proxy;
    this.redis_master = payload.redis_master;
    this.redis_slave = payload.redis_slave;
    this.cluster_shard_num = payload.cluster_shard_num;
    this.machine_pair_cnt = payload.machine_pair_cnt;
    this.cluster_stats = payload.cluster_stats || {};
    this.count = this.storageCount + this.proxyCount;
  }

  get isOnline() {
    return this.phase === 'online';
  }

  get isNew() {
    return isRecentDays(this.create_at, 24 * 3);
  }

  get redisMasterCount() {
    const len = this.redis_master.length;
    if (len <= 1) return len;
    return new Set(this.redis_master.map(item => item.ip)).size;
  }

  get redisMasterFaultNum() {
    const ips = this.redis_master.reduce((result, item) => {
      if (item.status !== 'running') {
        result.push(item.ip);
      }
      return result;
    }, [] as string[]);
    return new Set(ips).size;
  }

  get redisSlaveFaults() {
    const ips = this.redis_slave.reduce((result, item) => {
      if (item.status !== 'running') {
        result.push(item.ip);
      }
      return result;
    }, [] as string[]);
    return new Set(ips).size;
  }

  get redisSlaveCount() {
    const len = this.redis_slave.length;
    if (len <= 1) return len;
    return new Set(this.redis_slave.map(item => item.ip)).size;
  }

  get storageCount() {
    return this.redisMasterCount + this.redisSlaveCount;
  }

  get proxyCount() {
    const len = this.proxy.length;
    if (len <= 1) return len;
    return new Set(this.proxy.map(item => item.ip)).size;
  }

  get isSlaveNormal() {
    return this.redis_slave.every(item => item.status === 'running');
  }

  get masterDomainDisplayName() {
    const port = this.proxy[0]?.port;
    const displayName = port ? `${this.master_domain}:${port}` : this.master_domain;
    return displayName;
  }

  get isOnlineCLB() {
    return this.cluster_entry.some(item => item.cluster_entry_type === 'clb');
  }

  get isOnlinePolaris() {
    return this.cluster_entry.some(item => item.cluster_entry_type === 'polaris');
  }
}
