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

import { isRecentDays, utcDisplayTime } from '@utils';

import { t } from '@locales/index';

export default class InfluxDBInstance {
  static INFLUXDB_REBOOT = 'INFLUXDB_REBOOT';
  static INFLUXDB_REPLACE = 'INFLUXDB_REPLACE';
  static INFLUXDB_ENABLE = 'INFLUXDB_ENABLE';

  static operationIconMap = {
    [InfluxDBInstance.INFLUXDB_REBOOT]: 'zhongqizhong',
    [InfluxDBInstance.INFLUXDB_REPLACE]: 'tihuanzong',
    [InfluxDBInstance.INFLUXDB_ENABLE]: 'qiyongzhong',
  };

  static operationTextMap = {
    [InfluxDBInstance.INFLUXDB_REBOOT]: t('重启任务进行中'),
    [InfluxDBInstance.INFLUXDB_REPLACE]: t('替换任务进行中'),
    [InfluxDBInstance.INFLUXDB_ENABLE]: t('启用任务进行中'),
  };

  bk_cloud_id: number;
  bk_cloud_name: string;
  bk_host_id: number;
  create_at: string;
  restart_at: string;
  update_at: string;
  domain: string;
  id: number;
  instance_address: string;
  instance_name: string;
  operations: Array<{
    flow_id: number;
    instance_id: number;
    operator: string;
    status: string;
    ticket_id: number;
    ticket_type: string;
    title: string;
  }>;
  role: string;
  status: string;
  group_id: null | number;
  group_name: null | string;
  creator: string;
  phase: string;
  disk: number;
  cpu: number;
  mem: number;
  permission: Record<
    'influxdb_view' | 'influxdb_enable_disable' | 'influxdb_destroy' | 'influxdb_replace' | 'influxdb_reboot',
    boolean
  >;

  constructor(payload = {} as InfluxDBInstance) {
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.bk_host_id = payload.bk_host_id;
    this.create_at = payload.create_at;
    this.restart_at = payload.restart_at;
    this.update_at = payload.update_at;
    this.domain = payload.domain;
    this.id = payload.id;
    this.instance_address = payload.instance_address;
    this.instance_name = payload.instance_name;
    this.role = payload.role;
    this.status = payload.status;
    this.group_id = payload.group_id;
    this.group_name = payload.group_name;
    this.creator = payload.creator;
    this.phase = payload.phase;
    this.disk = payload.disk;
    this.mem = payload.mem;
    this.cpu = payload.cpu;
    this.permission = payload.permission || {};

    this.operations = this.initOperations(payload.operations);
  }

  get ip() {
    return this.instance_address.replace(/:.*/, '');
  }

  get isNew() {
    return isRecentDays(this.create_at, 24 * 3);
  }

  get runningOperation() {
    const operateTicketTypes = Object.keys(InfluxDBInstance.operationTextMap);
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
    return InfluxDBInstance.operationTextMap[this.operationRunningStatus];
  }

  // 操作中的状态 icon
  get operationStatusIcon() {
    return InfluxDBInstance.operationIconMap[this.operationRunningStatus];
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
    // // 实例异常不支持操作
    // if (this.status === STATUS_UNAVAILABLE) {
    //   return true;
    // }
    // 被禁用的实例不支持操作
    if (this.phase !== 'online') {
      return true;
    }
    // 各个操作互斥，有其他任务进行中禁用操作按钮
    if (this.operationTicketId) {
      return true;
    }
    return false;
  }

  get isOnline() {
    return this.phase === 'online';
  }

  get isOffline() {
    return this.phase === 'offline';
  }

  get isRebooting() {
    return Boolean(this.operations.find((item) => item.ticket_type === InfluxDBInstance.INFLUXDB_REBOOT));
  }

  get isStarting() {
    return Boolean(this.operations.find((item) => item.ticket_type === InfluxDBInstance.INFLUXDB_ENABLE));
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }

  get operationTagTips() {
    return this.operations.map((item) => ({
      icon: InfluxDBInstance.operationIconMap[item.ticket_type],
      tip: InfluxDBInstance.operationTextMap[item.ticket_type],
      ticketId: item.ticket_id,
    }));
  }

  initOperations(payload = [] as InfluxDBInstance['operations']) {
    if (!Array.isArray(payload)) {
      return [];
    }

    return payload;
  }
}
