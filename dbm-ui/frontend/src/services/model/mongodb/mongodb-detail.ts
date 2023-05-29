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

import { TicketTypes } from '@common/const';

import { utcDisplayTime } from '@utils';

import { t } from '@locales/index';

interface MongoInstance {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_host_id: number;
  bk_instance_id?: number;
  instance: string;
  ip: string;
  name?: string;
  phase: string;
  port: number;
  role?: string;
  spec_config: {
    id: number,
    cpu: {
      max: number,
      min: number
    },
    mem: {
      max: number,
      min: number
    },
    qps: {
      max: number,
      min: number
    },
    name: string,
    count: number,
    device_class: string[],
    storage_spec: {
      size: number,
      type: string,
      mount_point: string
    }[]
  }
  status: string;
}

export default class MongodbDetail {
  static operationIconMap: Record<string, string> = {
    [TicketTypes.MONGODB_ENABLE]: 'qiyongzhong',
    [TicketTypes.MONGODB_DISABLE]: 'jinyongzhong',
    [TicketTypes.MONGODB_DESTROY]: 'shanchuzhong',
  };

  static operationTextMap: Record<string, string> = {
    [TicketTypes.MONGODB_ENABLE]: t('启用任务进行中'),
    [TicketTypes.MONGODB_DISABLE]: t('禁用任务进行中'),
    [TicketTypes.MONGODB_DESTROY]: t('删除任务进行中'),
  };

  bk_biz_id: number;
  bk_biz_name: string;
  bk_cloud_id: number;
  bk_cloud_name: string;
  cluster_access_port: number;
  cluster_alias: string;
  cluster_entry_details: {
    cluster_entry_type: string;
    role: string;
    entry: string;
    target_details: {
      app: string,
      bk_cloud_iduid: number,
      dns_str: string,
      domain_name: string,
      domain_typeuid: number,
      ip: string,
      last_change_time: string,
      manager: string,
      port: number,
      remark: string,
      start_time: string,
      status: string,
      uid: number,
    }[];
  }[];
  cluster_id: number;
  cluster_name: string;
  cluster_type: string;
  create_at: string;
  creator: string;
  db_module_id: number;
  db_module_name: string;
  id: number;
  instances: {
    bk_cloud_id: number;
    bk_cloud_name: string;
    bk_host_id: number;
    cluster_id: number;
    cluster_name: string;
    cluster_type: string;
    create_at: string;
    host_info?: {
      alive: number,
      biz: {
        id: number,
        name: string
      },
      cloud_area: {
        id: number,
        name: string
      },
      cloud_id: number,
      host_id: number,
      host_name?: string,
      ip: string,
      ipv6: string,
      meta: {
        bk_biz_id: number,
        scope_id: number,
        scope_type: string
      },
      scope_id: string,
      scope_type: string,
      os_name: string,
      bk_cpu?: number,
      bk_disk?: number,
      bk_mem?: number,
      os_type: string,
      agent_id: number,
      cpu: string,
      cloud_vendor: string,
      bk_idc_name?: string,
    };
    instance_address: string;
    ip: string;
    master_domain: string;
    port: number;
    related_clusters: {
      alias: string;
      bk_biz_id: number;
      bk_cloud_id: number;
      cluster_name: string;
      cluster_type: string;
      creator: string;
      db_module_id: number;
      disaster_tolerance_level: string;
      id: number;
      major_version: string;
      master_domain: string;
      phase: string;
      region: string;
      status: string;
      time_zone: string;
      updater: string;
    }[];
    role: string;
    spec_config: string;
    status: string;
  }[];
  major_version: string;
  master_domain: string;
  mongodb: MongoInstance[];
  mongos: MongoInstance[];
  mongo_config: MongoInstance[];
  operations: {
    cluster_id: number,
    flow_id: number,
    status: string,
    ticket_id: number,
    ticket_type: string,
    title: string,
  }[];
  phase: string;
  phase_name: string;
  region: string;
  shard_node_count: number;
  shard_num: number;
  slave_domain: string;
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
  status: string;

  constructor(payload = {} as MongodbDetail) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.cluster_alias = payload.cluster_alias;
    this.cluster_access_port = payload.cluster_access_port;
    this.cluster_entry_details = payload.cluster_entry_details;
    this.cluster_id = payload.cluster_id;
    this.cluster_name = payload.cluster_name;
    this.cluster_type = payload.cluster_type;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.db_module_id = payload.db_module_id;
    this.db_module_name = payload.db_module_name;
    this.id = payload.id;
    this.instances = payload.instances;
    this.major_version = payload.major_version;
    this.master_domain = payload.master_domain;
    this.mongodb = payload.mongodb;
    this.mongos = payload.mongos;
    this.mongo_config = payload.mongo_config;
    this.operations = payload.operations;
    this.phase = payload.phase;
    this.phase_name = payload.phase_name;
    this.region = payload.region;
    this.shard_node_count = payload.shard_node_count;
    this.shard_num = payload.shard_num;
    this.slave_domain = payload.slave_domain;
    this.spec_config = payload.spec_config;
    this.status = payload.status;
  }

  get isOnline() {
    return this.phase === 'online';
  }

  get isOffline() {
    return this.phase === 'offline';
  }

  get isStarting() {
    return Boolean(this.operations.find(item => item.ticket_type === TicketTypes.MONGODB_ENABLE));
  }

  get runningOperation() {
    const operateTicketTypes = Object.keys(MongodbDetail.operationTextMap);
    return this.operations.find(item => operateTicketTypes.includes(item.ticket_type) && item.status === 'RUNNING');
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
    return MongodbDetail.operationTextMap[this.operationRunningStatus];
  }

  get operationStatusIcon() {
    return MongodbDetail.operationIconMap[this.operationRunningStatus];
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

  get isNormal() {
    return this.status === 'normal';
  }

  get masterDomainDisplayName() {
    return `${this.master_domain}:${this.cluster_access_port}`;
  }

  get isOfflineOperationRunning() {
    return ([
      TicketTypes.MONGODB_ENABLE,
      TicketTypes.MONGODB_DESTROY,
    ] as string[]).includes(this.operationRunningStatus);
  }

  get isDisabled() {
    return !this.isOnline && !this.isOfflineOperationRunning;
  }

  get operationTagTips() {
    return this.operations.map(item => ({
      icon: MongodbDetail.operationIconMap[item.ticket_type],
      tip: MongodbDetail.operationTextMap[item.ticket_type],
      ticketId: item.ticket_id,
    }));
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }
}
