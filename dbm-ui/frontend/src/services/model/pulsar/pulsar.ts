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

import { isRecentDays } from '@utils';

import { t } from '@locales/index';

// const STATUS_NORMAL = 'normal';
const STATUS_ABNORMAL = 'abnormal';

type Node = {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_host_id: number;
  bk_instance_id: number;
  instance: string;
  ip: string;
  name: string;
  phase: string;
  port: number;
  status: 'running' | 'unavailable'
}

export default class Pulsar {
  static PULSAR_SCALE_UP = 'PULSAR_SCALE_UP';
  static PULSAR_SHRINK = 'PULSAR_SHRINK';
  static PULSAR_REPLACE = 'PULSAR_REPLACE';
  static PULSAR_ENABLE = 'PULSAR_ENABLE';
  static PULSAR_DISABLE = 'PULSAR_DISABLE';
  static PULSAR_DESTROY = 'PULSAR_DESTROY';
  static PULSAR_REBOOT = 'PULSAR_REBOOT';

  static operationIconMap = {
    [Pulsar.PULSAR_SCALE_UP]: 'kuorongzhong',
    [Pulsar.PULSAR_SHRINK]: 'suorongzhong',
    [Pulsar.PULSAR_REPLACE]: 'tihuanzong',
    [Pulsar.PULSAR_ENABLE]: 'qiyongzhong',
    [Pulsar.PULSAR_DISABLE]: 'jinyongzhong',
    [Pulsar.PULSAR_DESTROY]: 'shanchuzhong',
    [Pulsar.PULSAR_REBOOT]: 'zhongqizhong',
  };

  static operationTextMap = {
    [Pulsar.PULSAR_SCALE_UP]: t('扩容任务进行中'),
    [Pulsar.PULSAR_SHRINK]: t('缩容任务进行中'),
    [Pulsar.PULSAR_REPLACE]: t('替换任务进行中'),
    [Pulsar.PULSAR_ENABLE]: t('启用任务进行中'),
    [Pulsar.PULSAR_DISABLE]: t('禁用任务进行中'),
    [Pulsar.PULSAR_DESTROY]: t('删除任务进行中'),
    [Pulsar.PULSAR_REBOOT]: t('实例重启任务进行中'),
  };

  access_url: string;
  bk_biz_id: number;
  bk_biz_name: string;
  bk_cloud_name: string;
  bk_cloud_id: number;
  cap_usage: number;
  cluster_alias: string;
  cluster_name: string;
  cluster_type: string;
  cluster_type_name: string;
  create_at: string;
  creator: string;
  domain: string;
  id: number;
  major_version: string;
  operations: Array<{
    cluster_id: number,
    flow_id: number,
    status: string,
    ticket_id: number,
    ticket_type: string,
    title: string,
  }>;
  phase: string;
  pulsar_bookkeeper: Node[];
  pulsar_broker: Node[];
  pulsar_zookeeper: Node[];
  status: string;
  update_at: string;
  updater: string;

  constructor(payload = {} as Pulsar) {
    this.access_url = payload.access_url;
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.cap_usage = payload.cap_usage;
    this.cluster_alias = payload.cluster_alias;
    this.cluster_name = payload.cluster_name;
    this.cluster_type = payload.cluster_type;
    this.cluster_type_name = payload.cluster_type_name;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.domain = payload.domain;
    this.id = payload.id;
    this.major_version = payload.major_version;
    this.phase = payload.phase;
    this.pulsar_bookkeeper = payload.pulsar_bookkeeper || [];
    this.pulsar_broker = payload.pulsar_broker || [];
    this.pulsar_zookeeper = payload.pulsar_zookeeper || [];
    this.status = payload.status;
    this.update_at = payload.update_at;
    this.updater = payload.updater;

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
    return Pulsar.operationTextMap[this.operationRunningStatus];
  }
  // 操作中的状态 icon
  get operationStatusIcon() {
    return Pulsar.operationIconMap[this.operationRunningStatus];
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
    if (this.operationRunningStatus) {
      return true;
    }
    return false;
  }

  get isOnline() {
    return this.phase === 'online';
  }

  get isNew() {
    return isRecentDays(this.create_at, 24 * 3);
  }

  initOperations(payload = [] as Pulsar['operations']) {
    if (!Array.isArray(payload)) {
      return [];
    }

    return payload;
  }
}
