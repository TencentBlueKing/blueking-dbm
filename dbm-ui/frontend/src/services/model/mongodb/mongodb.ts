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

import {
  PipelineStatus,
  TicketTypes,
} from '@common/const';

import { t } from '@locales/index';

interface MongoInstance {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_host_id: number;
  bk_instance_id: number;
  instance: string;
  ip: string;
  name: string;
  phase: string;
  port: number;
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
  status: 'running' | 'unavailable';
}

export default class Mongodb {
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
  cluster_name: string;
  cluster_type: string;
  create_at: string;
  creator: string;
  db_module_id: number;
  db_module_name: string;
  id: number;
  major_version: string;
  master_domain: string;
  mongo_config: MongoInstance[];
  mongodb: MongoInstance[];
  mongos: {
    admin_port: number;
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    bk_instance_id: number;
    instance: string;
    ip: string;
    name: string;
    phase: string;
    port: number;
    spec_config: string;
    status: 'running' | 'unavailable';
  }[];
  operations: {
    cluster_id: number;
    flow_id: number;
    operator: string;
    status: PipelineStatus;
    ticket_id: number;
    ticket_type: string;
    title: string;
  }[];
  phase: string;
  phase_name: string;
  region: string;
  slave_domain: string;
  shard_node_count: number; // 分片节点数
  shard_num: number; // 分片数
  status: string;

  constructor(payload = {} as Mongodb) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.db_module_id = payload.db_module_id;
    this.db_module_name = payload.db_module_name;
    this.cluster_access_port = payload.cluster_access_port;
    this.cluster_alias = payload.cluster_alias;
    this.cluster_name = payload.cluster_name;
    this.cluster_type = payload.cluster_type;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.id = payload.id;
    this.major_version = payload.major_version;
    this.master_domain = payload.master_domain;
    this.mongo_config = payload.mongo_config;
    this.mongodb = payload.mongodb;
    this.mongos = payload.mongos;
    this.operations = payload.operations;
    this.phase = payload.phase;
    this.phase_name = payload.phase_name;
    this.region = payload.region;
    this.status = payload.status;
    this.slave_domain = payload.slave_domain;
    this.shard_node_count = payload.shard_node_count;
    this.shard_num = payload.shard_num;
  }

  get isOnline() {
    return this.phase === 'online';
  }

  get isNewRow() {
    if (!this.create_at) {
      return '';
    }
    const createDay = dayjs(this.create_at);
    const today = dayjs();
    return today.diff(createDay, 'hour') <= 24;
  }

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

  get operationStatusText() {
    return Mongodb.operationTextMap[this.operationRunningStatus];
  }

  get operationStatusIcon() {
    return Mongodb.operationIconMap[this.operationRunningStatus];
  }

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
    if (!this.isClusterNormal) {
      return true;
    }

    if (this.operationRunningStatus) {
      return true;
    }
    return false;
  }

  get isClusterNormal() {
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
}
