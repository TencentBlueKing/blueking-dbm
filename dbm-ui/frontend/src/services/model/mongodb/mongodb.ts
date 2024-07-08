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

import dayjs from 'dayjs';
import { uniq } from 'lodash';

import { PipelineStatus, TicketTypes } from '@common/const';

import { utcDisplayTime } from '@utils';

import { t } from '@locales/index';

interface MongoInstance {
  bk_biz_id: number;
  bk_city: string;
  bk_cloud_id: number;
  bk_host_id: number;
  bk_instance_id: number;
  bk_sub_zone: string;
  bk_sub_zone_id: number;
  instance: string;
  ip: string;
  name: string;
  phase: string;
  port: number;
  spec_config: {
    id: number;
    cpu: {
      max: number;
      min: number;
    };
    mem: {
      max: number;
      min: number;
    };
    qps: {
      max: number;
      min: number;
    };
    name: string;
    count: number;
    device_class: string[];
    storage_spec: {
      size: number;
      type: string;
      mount_point: string;
    }[];
  };
  status: 'running' | 'unavailable';
}

export default class Mongodb {
  static MongoShardedCluster = 'MongoShardedCluster'; // 分片集群
  static MongoReplicaSet = 'MongoReplicaSet'; // 副本集集群

  static operationIconMap: Record<string, string> = {
    [TicketTypes.MONGODB_ENABLE]: t('启用中'),
    [TicketTypes.MONGODB_DISABLE]: t('禁用中'),
    [TicketTypes.MONGODB_DESTROY]: t('删除中'),
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
  cluster_name: string;
  cluster_stats: Record<'used' | 'total' | 'in_use', number>;
  cluster_time_zone: string;
  cluster_type: string;
  cluster_type_name: string;
  create_at: string;
  creator: string;
  db_module_id: number;
  db_module_name: string;
  disaster_tolerance_level: string;
  id: number;
  major_version: string;
  master_domain: string;
  machine_type: string;
  machine_instance_num: number;
  mongodb_machine_num: number;
  mongodb_machine_pair: number;
  mongo_config: MongoInstance[];
  mongodb: MongoInstance[];
  mongos: MongoInstance[];
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
    mongodb_view: boolean;
  };
  phase: string;
  phase_name: string;
  region: string;
  replicaset_machine_num: number;
  slave_domain: string;
  shard_node_count: number; // 分片节点数
  shard_num: number; // 分片数
  shard_spec: string;
  status: string;
  temporary_info: {
    source_cluster?: string;
    ticket_id: number;
  };
  update_at: string;
  updater: string;

  constructor(payload = {} as Mongodb) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.db_module_id = payload.db_module_id;
    this.db_module_name = payload.db_module_name;
    this.cluster_access_port = payload.cluster_access_port;
    this.cluster_alias = payload.cluster_alias;
    this.disaster_tolerance_level = payload.disaster_tolerance_level;
    this.cluster_name = payload.cluster_name;
    this.cluster_stats = payload.cluster_stats || {};
    this.cluster_time_zone = payload.cluster_time_zone;
    this.cluster_type = payload.cluster_type;
    this.cluster_type_name = payload.cluster_type_name;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.id = payload.id;
    this.major_version = payload.major_version;
    this.master_domain = payload.master_domain;
    this.machine_type = payload.machine_type;
    this.machine_instance_num = payload.machine_instance_num;
    this.mongodb_machine_num = payload.mongodb_machine_num;
    this.mongodb_machine_pair = payload.mongodb_machine_pair;
    this.mongo_config = payload.mongo_config;
    this.mongodb = payload.mongodb;
    this.mongos = payload.mongos;
    this.operations = payload.operations;
    this.permission = payload.permission;
    this.phase = payload.phase;
    this.phase_name = payload.phase_name;
    this.region = payload.region;
    this.replicaset_machine_num = payload.replicaset_machine_num;
    this.slave_domain = payload.slave_domain;
    this.shard_node_count = payload.shard_node_count;
    this.shard_num = payload.shard_num;
    this.temporary_info = payload.temporary_info;
    this.shard_spec = payload.shard_spec;
    this.status = payload.status;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }

  get isOnline() {
    return this.phase === 'online';
  }

  get isOffline() {
    return this.phase === 'offline';
  }

  get isStarting() {
    return Boolean(this.operations.find((item) => item.ticket_type === TicketTypes.MONGODB_ENABLE));
  }

  get allInstanceList() {
    return [...this.mongo_config, ...this.mongodb, ...this.mongos];
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
    const operateTicketTypes = Object.keys(Mongodb.operationTextMap);
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
    return Mongodb.operationTextMap[this.operationRunningStatus];
  }

  get operationStatusIcon() {
    return Mongodb.operationIconMap[this.operationRunningStatus];
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
    if (!this.create_at) {
      return '';
    }
    const createDay = dayjs(this.create_at);
    const today = dayjs();
    return today.diff(createDay, 'hour') <= 24;
  }

  get isNormal() {
    return this.status === 'normal';
  }

  get masterDomainDisplayName() {
    return `${this.master_domain}:${this.cluster_access_port}`;
  }

  get isOfflineOperationRunning() {
    return ([TicketTypes.MONGODB_ENABLE, TicketTypes.MONGODB_DESTROY] as string[]).includes(
      this.operationRunningStatus,
    );
  }

  get isDisabled() {
    return !this.isOnline && !this.isOfflineOperationRunning;
  }

  get operationTagTips() {
    return this.operations.map((item) => ({
      icon: Mongodb.operationIconMap[item.ticket_type],
      tip: Mongodb.operationTextMap[item.ticket_type],
      ticketId: item.ticket_id,
    }));
  }

  get isStructCluster() {
    return this.temporary_info?.source_cluster;
  }

  get clusterTypeText() {
    return this.cluster_type === Mongodb.MongoShardedCluster ? t('分片') : t('副本集');
  }

  get instanceCount() {
    if (this.cluster_type === Mongodb.MongoShardedCluster) {
      return this.mongo_config.length + this.mongos.length + this.mongodb.length;
    }
    return this.mongodb.length;
  }

  get isMongoReplicaSet() {
    return this.cluster_type === 'MongoReplicaSet';
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at);
  }
}
