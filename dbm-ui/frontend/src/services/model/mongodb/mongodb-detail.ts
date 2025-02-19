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

import ClusterEntryDetailModel from '@services/model/cluster-entry/cluster-entry-details';
import type { ClusterListEntry, ClusterListSpec } from '@services/types';

import { ClusterAffinityMap, TicketTypes } from '@common/const';

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
    qps: {
      max: number;
      min: number;
    };
    storage_spec: {
      mount_point: string;
      size: number;
      type: string;
    }[];
  };
  status: string;
}

export default class MongodbDetail {
  static operationIconMap: Record<string, string> = {
    [TicketTypes.MONGODB_DESTROY]: t('删除中'),
    [TicketTypes.MONGODB_DISABLE]: t('禁用中'),
    [TicketTypes.MONGODB_ENABLE]: t('启用中'),
  };

  static operationTextMap: Record<string, string> = {
    [TicketTypes.MONGODB_DESTROY]: t('删除任务进行中'),
    [TicketTypes.MONGODB_DISABLE]: t('禁用任务进行中'),
    [TicketTypes.MONGODB_ENABLE]: t('启用任务进行中'),
  };

  bk_biz_id: number;
  bk_biz_name: string;
  bk_cloud_id: number;
  bk_cloud_name: string;
  cluster_access_port: number;
  cluster_alias: string;
  cluster_entry: ClusterListEntry[];
  cluster_entry_details: ClusterEntryDetailModel[];
  cluster_id: number;
  cluster_name: string;
  cluster_spec: ClusterListSpec;
  cluster_type: string;
  create_at: string;
  creator: string;
  db_module_id: number;
  db_module_name: string;
  disaster_tolerance_level: keyof typeof ClusterAffinityMap;
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
      agent_id: number;
      alive: number;
      biz: {
        id: number;
        name: string;
      };
      bk_cpu?: number;
      bk_disk?: number;
      bk_idc_name?: string;
      bk_mem?: number;
      cloud_area: {
        id: number;
        name: string;
      };
      cloud_id: number;
      cloud_vendor: string;
      cpu: string;
      host_id: number;
      host_name?: string;
      ip: string;
      ipv6: string;
      meta: {
        bk_biz_id: number;
        scope_id: number;
        scope_type: string;
      };
      os_name: string;
      os_type: string;
      scope_id: string;
      scope_type: string;
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
  mongo_config: MongoInstance[];
  mongodb: MongoInstance[];
  mongos: MongoInstance[];
  operations: {
    cluster_id: number;
    flow_id: number;
    status: string;
    ticket_id: number;
    ticket_type: string;
    title: string;
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
    };
    id: number;
    mem: {
      max: number;
      min: number;
    };
    name: string;
    qps: {
      max: number;
      min: number;
    };
    storage_spec: {
      mount_point: string;
      size: number;
      type: string;
    }[];
  };
  status: string;

  constructor(payload = {} as MongodbDetail) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.cluster_alias = payload.cluster_alias;
    this.cluster_access_port = payload.cluster_access_port;
    this.cluster_entry = payload.cluster_entry || [];
    this.cluster_entry_details = payload.cluster_entry_details.map((item) => new ClusterEntryDetailModel(item));
    this.cluster_id = payload.cluster_id;
    this.cluster_name = payload.cluster_name;
    this.cluster_spec = payload.cluster_spec;
    this.cluster_type = payload.cluster_type;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.db_module_id = payload.db_module_id;
    this.db_module_name = payload.db_module_name;
    this.disaster_tolerance_level = payload.disaster_tolerance_level;
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

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }

  get disasterToleranceLevelName() {
    return ClusterAffinityMap[this.disaster_tolerance_level];
  }

  get entryAccess() {
    if (this.isMongoReplicaSet) {
      return `mongodb://{username}:{password}@${this.entryDomain}/?replicaSet=${this.cluster_name}&authSource=admin`;
    }
    return `mongodb://{username}:{password}@${this.entryDomain}/?authSource=admin`;
  }

  get entryAccessClb() {
    if (!this.isMongoReplicaSet) {
      const clbItem = this.cluster_entry.find((entryItem) => entryItem.cluster_entry_type === 'clbDns');
      if (clbItem) {
        return `mongodb://{username}:{password}@${clbItem.entry}:${this.cluster_access_port}/?authSource=admin`;
      }
    }
    return '';
  }

  get entryDomain() {
    if (this.isMongoReplicaSet) {
      const domainList = this.cluster_entry.reduce<string[]>((prevDomainList, entryItem) => {
        if (!entryItem.entry.includes('backup')) {
          return prevDomainList.concat(`${entryItem.entry}:${this.cluster_access_port}`);
        }
        return prevDomainList;
      }, []);
      return domainList.join(',');
    }
    return `${this.master_domain}:${this.cluster_access_port}`;
  }

  get isDisabled() {
    return !this.isOnline && !this.isOfflineOperationRunning;
  }

  get isMongoReplicaSet() {
    return this.cluster_type === 'MongoReplicaSet';
  }

  get isNormal() {
    return this.status === 'normal';
  }

  get isOffline() {
    return this.phase === 'offline';
  }

  get isOfflineOperationRunning() {
    return ([TicketTypes.MONGODB_ENABLE, TicketTypes.MONGODB_DESTROY] as string[]).includes(
      this.operationRunningStatus,
    );
  }

  get isOnline() {
    return this.phase === 'online';
  }

  get isStarting() {
    return Boolean(this.operations.find((item) => item.ticket_type === TicketTypes.MONGODB_ENABLE));
  }

  get masterDomainDisplayName() {
    return `${this.master_domain}:${this.cluster_access_port}`;
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

  get operationStatusIcon() {
    return MongodbDetail.operationIconMap[this.operationRunningStatus];
  }

  // 操作中的状态描述文本
  get operationStatusText() {
    return MongodbDetail.operationTextMap[this.operationRunningStatus];
  }

  get operationTagTips() {
    return this.operations.map((item) => ({
      icon: MongodbDetail.operationIconMap[item.ticket_type],
      ticketId: item.ticket_id,
      tip: MongodbDetail.operationTextMap[item.ticket_type],
    }));
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

  get runningOperation() {
    const operateTicketTypes = Object.keys(MongodbDetail.operationTextMap);
    return this.operations.find((item) => operateTicketTypes.includes(item.ticket_type) && item.status === 'RUNNING');
  }
}
