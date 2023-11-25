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

import type ResourceSpecModel from '@services/model/resource-spec/resourceSpec';

import { t } from '@locales/index';

const STATUS_ABNORMAL = 'abnormal';

export type InstanceSpecInfo = {
  count: number,
  id: number,
  name: string,
  cpu: {
    max: number,
    min: number
  },
  mem: {
    max: number,
    min: number
  },
  storage_spec: {
    mount_point: string,
    size: number | string,
    type: string,
  }[],
  device_class: string[],
  qps: {
    min: number,
    max: number
  },
}

export type Instance = {
  bk_biz_id: number,
  bk_cloud_id: number,
  bk_host_id: number,
  bk_instance_id: number,
  instance: string,
  ip: string,
  name: string,
  phase: 'online' | 'offline',
  port: number,
  status: 'running' | 'unavailable',
  spec_config: InstanceSpecInfo,
  shard_id?: number
}

export default class TendbCluster {
  static TENDBCLUSTER_SPIDER_ADD_NODES = 'TENDBCLUSTER_SPIDER_ADD_NODES';
  static TENDBCLUSTER_SPIDER_REDUCE_NODES = 'TENDBCLUSTER_SPIDER_REDUCE_NODES';
  static TENDBCLUSTER_ENABLE = 'TENDBCLUSTER_ENABLE';
  static TENDBCLUSTER_DISABLE = 'TENDBCLUSTER_DISABLE';
  static TENDBCLUSTER_DESTROY = 'TENDBCLUSTER_DESTROY';

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
  };

  bk_biz_id: number;
  bk_biz_name: string;
  bk_cloud_id: number;
  bk_cloud_name: string;
  cluster_capacity: number;
  cluster_name: string;
  cluster_shard_num: number;
  cluster_spec: ResourceSpecModel;
  cluster_type: string;
  create_at: string;
  creator: string;
  db_module_id: number;
  db_module_name: string;
  id: number;
  machine_pair_cnt: number;
  major_version: string;
  master_domain: string;
  operations: Array<{
    cluster_id: number,
    flow_id: number,
    status: string,
    ticket_id: number,
    ticket_type: string,
    title: string,
    operationStatusText: string,
    operationStatusIcon: string,
    operationTicketId: number,
    operationDisabled: boolean
  }>;
  phase: 'online' | 'offline';
  region: string;
  remote_db: Instance[];
  remote_dr: Instance[];
  remote_shard_num: number;
  slave_domain: string;
  spider_master: Instance[];
  spider_mnt: Instance[];
  spider_slave: Instance[];
  status: string;
  temporary_info: {
    source_cluster?: string,
    ticket_id: number
  };

  constructor(payload = {} as TendbCluster) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.cluster_capacity = payload.cluster_capacity;
    this.cluster_name = payload.cluster_name;
    this.cluster_shard_num = payload.cluster_shard_num;
    this.cluster_spec = payload.cluster_spec;
    this.cluster_type = payload.cluster_type;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.db_module_id = payload.db_module_id;
    this.db_module_name = payload.db_module_name;
    this.id = payload.id;
    this.machine_pair_cnt = payload.machine_pair_cnt;
    this.major_version = payload.major_version;
    this.master_domain = payload.master_domain;
    this.phase = payload.phase;
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
    this.operations = this.initOperations(payload.operations);
  }

  // 操作中的状态
  get operationRunningStatus() {
    if (this.operations.length < 1) {
      return '';
    }
    const operation = this.operations[0];
    if (operation.status !== 'RUNNING') {
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
    const operation = this.operations[0];
    if (operation.status !== 'RUNNING') {
      return 0;
    }
    return operation.ticket_id;
  }

  get operationDisabled() {
    // 集群异常不支持操作
    if (this.status === STATUS_ABNORMAL) {
      return true;
    }
    // 被禁用的集群不支持操作
    if (this.phase !== 'online') {
      return true;
    }

    // 各个操作互斥，有其他任务进行中禁用操作按钮
    if (this.operations.find(item => item.status === 'RUNNING')) {
      return true;
    }
    return false;
  }

  get isOnline() {
    return this.phase === 'online';
  }

  initOperations(payload = [] as TendbCluster['operations']) {
    if (!Array.isArray(payload)) {
      return [];
    }
    return payload;
  }
}
