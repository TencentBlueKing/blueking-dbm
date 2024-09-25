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

export type InstanceSpecInfo = {
  count: number;
  cpu: {
    max: number;
    min: number;
  };
  device_class: string[];
  id: number;
  mem: {
    max: number;
    min: number;
  };
  name: string;
  storage_spec: {
    mount_point: string;
    size: number;
    type: string;
  }[];
  qps: {
    min: number;
    max: number;
  };
};

export default class TendbCluster {
  static TENDBCLUSTER_SPIDER_ADD_NODES = 'TENDBCLUSTER_SPIDER_ADD_NODES';
  static TENDBCLUSTER_SPIDER_REDUCE_NODES = 'TENDBCLUSTER_SPIDER_REDUCE_NODES';
  static TENDBCLUSTER_ENABLE = 'TENDBCLUSTER_ENABLE';
  static TENDBCLUSTER_DISABLE = 'TENDBCLUSTER_DISABLE';
  static TENDBCLUSTER_DESTROY = 'TENDBCLUSTER_DESTROY';
  static MYSQL_OPEN_AREA = 'MYSQL_OPEN_AREA';
  static TENDBCLUSTER_CHECKSUM = 'TENDBCLUSTER_CHECKSUM';

  static operationIconMap = {
    [TendbCluster.TENDBCLUSTER_SPIDER_ADD_NODES]: 'kuorongzhong',
    [TendbCluster.TENDBCLUSTER_SPIDER_REDUCE_NODES]: 'suorongzhong',
    [TendbCluster.TENDBCLUSTER_ENABLE]: 'qiyongzhong',
    [TendbCluster.TENDBCLUSTER_DISABLE]: 'jinyongzhong',
    [TendbCluster.TENDBCLUSTER_DESTROY]: 'shanchuzhong',
  };

  static operationTextMap = {
    [TendbCluster.TENDBCLUSTER_SPIDER_ADD_NODES]: t('扩容任务进行中'),
    [TendbCluster.TENDBCLUSTER_SPIDER_REDUCE_NODES]: t('缩容任务进行中'),
    [TendbCluster.TENDBCLUSTER_ENABLE]: t('启用任务进行中'),
    [TendbCluster.TENDBCLUSTER_DISABLE]: t('禁用任务进行中'),
    [TendbCluster.TENDBCLUSTER_DESTROY]: t('删除任务进行中'),
    [TendbCluster.MYSQL_OPEN_AREA]: t('开区任务进行中'),
    [TendbCluster.TENDBCLUSTER_CHECKSUM]: t('数据校验修复任务进行中'),
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
  id: number;
  machine_pair_cnt: number;
  major_version: string;
  master_domain: string;
  operations: ClusterListOperation[];
  permission: {
    tendbcluster_destroy: boolean;
    tendbcluster_dump_data: boolean;
    tendbcluster_enable_disable: boolean;
    tendbcluster_node_rebalance: boolean;
    tendbcluster_spider_add_nodes: boolean;
    tendbcluster_spider_mnt_destroy: boolean;
    tendbcluster_spider_reduce_nodes: boolean;
    tendbcluster_view: boolean;
    tendb_spider_slave_destroy: boolean;
    tendbcluster_webconsole: boolean;
    access_entry_edit: boolean;
  };
  phase: 'online' | 'offline';
  phase_name: string;
  region: string;
  remote_db: ClusterListNode[];
  remote_dr: ClusterListNode[];
  remote_shard_num: number;
  slave_domain: string;
  spider_master: ClusterListNode[];
  spider_mnt: ClusterListNode[];
  spider_slave: ClusterListNode[];
  status: string;
  temporary_info: {
    source_cluster: string;
    ticket_id: number;
  };
  update_at: string;
  updater: string;

  constructor(payload = {} as TendbCluster) {
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
    this.cluster_type = payload.cluster_type;
    this.cluster_type_name = payload.cluster_type_name;
    this.cluster_time_zone = payload.cluster_time_zone;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.db_module_id = payload.db_module_id;
    this.db_module_name = payload.db_module_name;
    this.id = payload.id;
    this.machine_pair_cnt = payload.machine_pair_cnt;
    this.major_version = payload.major_version;
    this.master_domain = payload.master_domain;
    this.operations = payload.operations || [];
    this.permission = payload.permission || {};
    this.phase = payload.phase;
    this.phase_name = payload.phase_name;
    this.region = payload.region;
    this.remote_db = payload.remote_db;
    this.remote_dr = payload.remote_dr;
    this.remote_shard_num = payload.remote_shard_num;
    this.slave_domain = payload.slave_domain;
    this.spider_master = payload.spider_master;
    this.spider_mnt = payload.spider_mnt;
    this.spider_slave = payload.spider_slave;
    this.status = payload.status;
    this.temporary_info = payload.temporary_info;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }

  get allInstanceList() {
    return [...this.spider_master, ...this.spider_slave, ...this.spider_mnt, ...this.remote_db, ...this.remote_dr];
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
    const operateTicketTypes = Object.keys(TendbCluster.operationTextMap);
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
    return TendbCluster.operationTextMap[this.operationRunningStatus];
  }

  // 操作中的状态 icon
  get operationStatusIcon() {
    return TendbCluster.operationIconMap[this.operationRunningStatus];
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

  get isNew() {
    return isRecentDays(this.create_at, 24 * 3);
  }

  get isOnline() {
    return this.phase === 'online';
  }

  get isOffline() {
    return this.phase === 'offline';
  }

  get isStarting() {
    return Boolean(this.operations.find((item) => item.ticket_type === TendbCluster.TENDBCLUSTER_ENABLE));
  }

  get isTemporary() {
    return Object.keys(this.temporary_info).length > 0;
  }

  get masterDomainDisplayName() {
    const port = this.spider_master[0]?.port;
    const displayName = port ? `${this.master_domain}:${port}` : this.master_domain;
    return displayName;
  }

  get slaveDomainDisplayName() {
    const port = this.spider_slave[0]?.port;
    const displayName = port ? `${this.slave_domain}:${port}` : this.slave_domain;
    return this.slave_domain ? displayName : '--';
  }

  get operationTagTips() {
    return this.operations.map((item) => ({
      icon: TendbCluster.operationIconMap[item.ticket_type],
      tip: TendbCluster.operationTextMap[item.ticket_type],
      ticketId: item.ticket_id,
    }));
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }
}
