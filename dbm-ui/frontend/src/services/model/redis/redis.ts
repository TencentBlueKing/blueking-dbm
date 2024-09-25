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
import { uniq } from 'lodash';

import type { ClusterListEntry, ClusterListNode, ClusterListOperation, ClusterListSpec } from '@services/types';

import { isRecentDays, utcDisplayTime } from '@utils';

import { t } from '@locales/index';

export const enum RedisClusterTypes {
  PredixyTendisplusCluster = 'PredixyTendisplusCluster', // Tendisplus
  PredixyRedisCluster = 'PredixyRedisCluster',
  RedisInstance = 'RedisInstance',
  TwemproxyRedisInstance = 'TwemproxyRedisInstance', // TendisCache
  TwemproxyTendisSSDInstance = 'TwemproxyTendisSSDInstance', // TendisSSD
}

export default class Redis {
  static REDIS_DESTROY = 'REDIS_DESTROY';
  static REDIS_PROXY_CLOSE = 'REDIS_PROXY_CLOSE';
  static REDIS_PROXY_OPEN = 'REDIS_PROXY_OPEN';
  static REDIS_INSTANCE_DESTROY = 'REDIS_INSTANCE_DESTROY';
  static REDIS_INSTANCE_CLOSE = 'REDIS_INSTANCE_CLOSE';
  static REDIS_INSTANCE_OPEN = 'REDIS_INSTANCE_OPEN';

  static operationIconMap = {
    [Redis.REDIS_PROXY_OPEN]: 'qiyongzhong',
    [Redis.REDIS_PROXY_CLOSE]: 'jinyongzhong',
    [Redis.REDIS_DESTROY]: 'shanchuzhong',
    [Redis.REDIS_INSTANCE_OPEN]: 'qiyongzhong',
    [Redis.REDIS_INSTANCE_CLOSE]: 'jinyongzhong',
    [Redis.REDIS_INSTANCE_DESTROY]: 'shanchuzhong',
  };

  static operationTextMap = {
    [Redis.REDIS_DESTROY]: t('删除任务执行中'),
    [Redis.REDIS_PROXY_CLOSE]: t('禁用任务执行中'),
    [Redis.REDIS_PROXY_OPEN]: t('启用任务执行中'),
    [Redis.REDIS_INSTANCE_DESTROY]: t('删除任务执行中'),
    [Redis.REDIS_INSTANCE_CLOSE]: t('禁用任务执行中'),
    [Redis.REDIS_INSTANCE_OPEN]: t('启用任务执行中'),
  };

  bk_biz_id: number;
  bk_biz_name: string;
  bk_cloud_id: number;
  bk_cloud_name: string;
  cluster_access_port: number;
  cluster_alias: string;
  cluster_capacity: number;
  cluster_entry: ClusterListEntry[];
  cluster_name: string;
  cluster_shard_num: number;
  cluster_spec: ClusterListSpec;
  cluster_stats: Record<'used' | 'total' | 'in_use', number>;
  cluster_time_zone: string;
  cluster_type: string;
  cluster_type_name: string;
  create_at: string;
  creator: string;
  db_module_id: number;
  db_module_name: string;
  dns_to_clb: boolean;
  id: number;
  machine_pair_cnt: number;
  major_version: string;
  master_domain: string;
  operations: ClusterListOperation[];
  permission: {
    access_entry_edit: boolean;
    redis_access_entry_view: boolean;
    redis_backup: boolean;
    redis_destroy: boolean;
    redis_keys_delete: boolean;
    redis_keys_extract: boolean;
    redis_open_close: boolean;
    redis_plugin_create_clb: boolean;
    redis_plugin_create_polaris: boolean;
    redis_plugin_dns_bind_clb: boolean;
    redis_purge: boolean;
    redis_view: boolean;
    redis_webconsole: boolean;
  };
  phase: string;
  phase_name: string;
  proxy: ClusterListNode[];
  redis_master: ClusterListNode[];
  redis_slave: ClusterListNode[];
  region: string;
  slave_domain: string;
  status: string;
  update_at: string;
  updater: string;

  constructor(payload = {} as Redis) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.cluster_access_port = payload.cluster_access_port;
    this.cluster_alias = payload.cluster_alias;
    this.cluster_capacity = payload.cluster_capacity;
    this.cluster_entry = payload.cluster_entry || [];
    this.cluster_name = payload.cluster_name;
    this.cluster_shard_num = payload.cluster_shard_num;
    this.cluster_spec = payload.cluster_spec;
    this.cluster_stats = payload.cluster_stats || {};
    this.cluster_time_zone = payload.cluster_time_zone;
    this.cluster_type = payload.cluster_type;
    this.cluster_type_name = payload.cluster_type_name;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.db_module_id = payload.db_module_id;
    this.db_module_name = payload.db_module_name;
    this.dns_to_clb = payload.dns_to_clb;
    this.id = payload.id;
    this.machine_pair_cnt = payload.machine_pair_cnt;
    this.major_version = payload.major_version;
    this.master_domain = payload.master_domain;
    this.operations = payload.operations || [];
    this.permission = payload.permission || {};
    this.phase = payload.phase;
    this.phase_name = payload.phase_name;
    this.proxy = payload.proxy || [];
    this.redis_master = payload.redis_master || [];
    this.redis_slave = payload.redis_slave || [];
    this.region = payload.region;
    this.slave_domain = payload.slave_domain;
    this.status = payload.status;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }

  get isOnline() {
    return this.phase === 'online';
  }

  get isNew() {
    return isRecentDays(this.create_at, 24 * 3);
  }

  get redisMasterCount() {
    const len = this.redis_master.length;
    if (len <= 1) {
      return len;
    }
    return new Set(this.redis_master.map((item) => item.ip)).size;
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
    if (len <= 1) {
      return len;
    }
    return new Set(this.redis_slave.map((item) => item.ip)).size;
  }

  get storageCount() {
    return this.redisMasterCount + this.redisSlaveCount;
  }

  get proxyCount() {
    const len = this.proxy.length;
    if (len <= 1) {
      return len;
    }
    return new Set(this.proxy.map((item) => item.ip)).size;
  }

  get count() {
    return this.storageCount + this.proxyCount;
  }

  get isSlaveNormal() {
    return this.redis_slave.every((item) => item.status === 'running');
  }

  get masterDomainDisplayName() {
    const port = this.proxy[0]?.port;
    const displayName = port ? `${this.master_domain}:${port}` : this.master_domain;
    return displayName;
  }

  get redisInstanceMasterDomainDisplayName() {
    const port = this.cluster_access_port;
    const displayName = port ? `${this.master_domain}:${port}` : this.master_domain;
    return displayName;
  }

  get redisInstanceSlaveDomainDisplayName() {
    const port = this.cluster_access_port;
    const displayName = port ? `${this.slave_domain}:${port}` : this.slave_domain;
    return this.slave_domain ? displayName : '--';
  }

  get isOnlineCLB() {
    return this.cluster_entry.some((item) => item.cluster_entry_type === 'clb');
  }

  get isOnlinePolaris() {
    return this.cluster_entry.some((item) => item.cluster_entry_type === 'polaris');
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at);
  }

  get isOffline() {
    return this.phase === 'offline';
  }

  get isStarting() {
    return Boolean(this.operations.find((item) => item.ticket_type === Redis.REDIS_PROXY_OPEN));
  }

  get allInstanceList() {
    return [...this.proxy, ...this.redis_master, ...this.redis_slave];
  }

  get allIPList() {
    return uniq(this.allInstanceList.map((item) => item.ip));
  }

  // 异常主机IP
  get allUnavailableIPList() {
    return uniq(
      this.allInstanceList.reduce(
        (pre, cur) => [...pre, ...(cur.status === 'unavailable' ? [cur.ip] : [])],
        [] as string[],
      ),
    );
  }

  get runningOperation() {
    const operateTicketTypes = Object.keys(Redis.operationTextMap);
    return this.operations.find((item) => operateTicketTypes.includes(item.ticket_type) && item.status === 'RUNNING');
  }

  // 操作中的状态
  get operationRunningStatus() {
    if (this.operations.length < 1) {
      return '';
    }
    const operation = this.runningOperation;
    if (!operation) {
      return '';
    }
    return operation.ticket_type;
  }

  // 操作中的状态描述文本
  get operationStatusText() {
    return Redis.operationTextMap[this.operationRunningStatus];
  }

  // 操作中的单据 ID
  get operationTicketId() {
    if (this.operations.length < 1) {
      return 0;
    }
    const operation = this.runningOperation;
    if (!operation) {
      return 0;
    }
    return operation.ticket_id;
  }

  get operationDisabled() {
    // 集群异常不支持操作
    if (this.status === 'abnormal') {
      return true;
    }
    // 被禁用的集群不支持操作
    if (this.phase !== 'online') {
      return true;
    }

    // 各个操作互斥，有其他任务进行中禁用操作按钮
    if (this.operationTicketId) {
      return true;
    }
    return false;
  }

  get operationTagTips() {
    return this.operations.map((item) => ({
      icon: Redis.operationIconMap[item.ticket_type],
      tip: Redis.operationTextMap[item.ticket_type],
      ticketId: item.ticket_id,
    }));
  }
}
