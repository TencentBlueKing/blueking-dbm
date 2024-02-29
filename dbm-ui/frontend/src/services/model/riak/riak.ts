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

import { utcDisplayTime } from '@utils';

import { t } from '@locales/index';

export default class Riak {
  static RIAK_CLUSTER_SCALE_OUT = 'RIAK_CLUSTER_SCALE_OUT';
  static RIAK_CLUSTER_SCALE_IN = 'RIAK_CLUSTER_SCALE_IN';
  static RIAK_CLUSTER_ENABLE = 'RIAK_CLUSTER_ENABLE';
  static RIAK_CLUSTER_DISABLE = 'RIAK_CLUSTER_DISABLE';
  static RIAK_CLUSTER_DESTROY = 'RIAK_CLUSTER_DESTROY';
  static RIAK_CLUSTER_REBOOT = 'RIAK_CLUSTER_REBOOT';

  static operationIconMap: Record<string, string> = {
    [Riak.RIAK_CLUSTER_SCALE_OUT]: 'kuorongzhong',
    [Riak.RIAK_CLUSTER_SCALE_IN]: 'suorongzhong',
    [Riak.RIAK_CLUSTER_ENABLE]: 'qiyongzhong',
    [Riak.RIAK_CLUSTER_DISABLE]: 'jinyongzhong',
    [Riak.RIAK_CLUSTER_DESTROY]: 'shanchuzhong',
    [Riak.RIAK_CLUSTER_REBOOT]: 'zhongqizhong',
  };

  static operationTextMap: Record<string, string> = {
    [Riak.RIAK_CLUSTER_SCALE_OUT]: t('扩容任务进行中'),
    [Riak.RIAK_CLUSTER_SCALE_IN]: t('缩容任务进行中'),
    [Riak.RIAK_CLUSTER_ENABLE]: t('启用任务进行中'),
    [Riak.RIAK_CLUSTER_DISABLE]: t('禁用任务进行中'),
    [Riak.RIAK_CLUSTER_DESTROY]: t('删除任务进行中'),
    [Riak.RIAK_CLUSTER_REBOOT]: t('重启任务进行中'),
  };

  id: number;
  phase: 'online' | 'offline';
  phase_name: string;
  status: 'normal' | 'abnormal';
  cluster_name: string;
  cluster_alias: string;
  major_version: string;
  bk_biz_id: number;
  bk_biz_name: string;
  bk_cloud_id: number;
  bk_cloud_name: string;
  cluster_type: string;
  cluster_type_name: string;
  operations: Array<{
    cluster_id: number;
    flow_id: number;
    operator: string;
    status: string;
    ticket_id: number;
    ticket_type: string;
    title: string;
  }>;
  riak_node: Array<{
    name: string;
    ip: string;
    port: number;
    instance: string;
    status: 'running' | 'unavailable';
    phase: string;
    bk_instance_id: number;
    bk_host_id: number;
    bk_cloud_id: number;
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
      device_class: Array<unknown>;
      storage_spec: Array<{
        size: number;
        type: string;
        mount_point: string;
      }>;
    };
  }>;
  domain: string;
  creator: string;
  updater: string;
  create_at: string;
  update_at: string;
  access_url: string;
  cap_usage: number;
  db_module_id: number;
  db_module_name: string;

  constructor(payload = {} as Riak) {
    this.id = payload.id;
    this.phase = payload.phase;
    this.phase_name = payload.phase_name;
    this.status = payload.status;
    this.cluster_name = payload.cluster_name;
    this.cluster_alias = payload.cluster_alias;
    this.major_version = payload.major_version;
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.cluster_type = payload.cluster_type;
    this.cluster_type_name = payload.cluster_type_name;
    this.operations = payload.operations;
    this.riak_node = payload.riak_node;
    this.domain = payload.domain;
    this.creator = payload.creator;
    this.updater = payload.updater;
    this.create_at = payload.create_at;
    this.update_at = payload.update_at;
    this.access_url = payload.access_url;
    this.cap_usage = payload.cap_usage;
    this.db_module_id = payload.db_module_id;
    this.db_module_name = payload.db_module_name;
  }

  get isNewRow() {
    if (!this.create_at) {
      return '';
    }

    const createDay = dayjs(this.create_at);
    const today = dayjs();
    return today.diff(createDay, 'hour') <= 24;
  }

  get runningOperation() {
    const operateTicketTypes = Object.keys(Riak.operationTextMap);
    return this.operations.find((item) => operateTicketTypes.includes(item.ticket_type) && item.status === 'RUNNING');
  }

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

  get operationStatusText() {
    return Riak.operationTextMap[this.operationRunningStatus];
  }

  get operationStatusIcon() {
    return Riak.operationIconMap[this.operationRunningStatus];
  }

  get isOfflineOperationRunning() {
    return ([Riak.RIAK_CLUSTER_ENABLE, Riak.RIAK_CLUSTER_DESTROY] as string[]).includes(this.operationRunningStatus);
  }

  get isDisabled() {
    return !this.isOnline && !this.isOfflineOperationRunning;
  }

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
    if (!this.isClusterNormal) {
      return true;
    }

    // if (!this.isOnline) {
    //   return true;
    // }

    if (this.operationTicketId) {
      return true;
    }
    return false;
  }

  get isClusterNormal() {
    return this.status === 'normal';
  }

  get isOnline() {
    return this.phase === 'online';
  }

  get isStarting() {
    return Boolean(this.operations.find((item) => item.ticket_type === Riak.RIAK_CLUSTER_ENABLE));
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }

  get operationTagTips() {
    return this.operations.map((item) => ({
      icon: Riak.operationIconMap[item.ticket_type],
      tip: Riak.operationTextMap[item.ticket_type],
      ticketId: item.ticket_id,
    }));
  }
}
