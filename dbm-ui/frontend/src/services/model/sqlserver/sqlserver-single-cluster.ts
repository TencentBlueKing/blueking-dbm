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

import { PipelineStatus } from '@common/const';

import { t } from '@locales/index';

import TimeBaseClassModel from '../utils/time-base-class';

export default class SqlServerSingleCluster extends TimeBaseClassModel {
  static SQLSERVER_DESTROY = 'SQLSERVER_DESTROY';
  static SQLSERVER_DISABLE = 'SQLSERVER_DISABLE';
  static SQLSERVER_ENABLE = 'SQLSERVER_ENABLE';
  static operationIconMap = {
    [SqlServerSingleCluster.SQLSERVER_ENABLE]: 'qiyongzhong',
    [SqlServerSingleCluster.SQLSERVER_DISABLE]: 'jinyongzhong',
    [SqlServerSingleCluster.SQLSERVER_DESTROY]: 'shanchuzhong',
  };
  static operationTextMap = {
    [SqlServerSingleCluster.SQLSERVER_DESTROY]: t('删除任务执行中'),
    [SqlServerSingleCluster.SQLSERVER_DISABLE]: t('禁用任务执行中'),
    [SqlServerSingleCluster.SQLSERVER_ENABLE]: t('启用任务执行中'),
  };
  static statusMap: Record<string, string> = {
    running: t('正常'),
    unavailable: t('异常'),
  };
  static themes: Record<string, string> = {
    running: 'success',
  };

  bk_biz_id: number;
  bk_biz_name: string;
  bk_cloud_id: number;
  bk_cloud_name: string;
  cluster_alias: string;
  cluster_name: string;
  cluster_time_zone: string;
  cluster_type: string;
  cluster_type_name: string;
  creator: string;
  db_module_id: number;
  db_module_name: string;
  id: number;
  major_version: string;
  master_domain: string;
  masters: {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    bk_instance_id: number;
    instance: string;
    ip: string;
    name: string;
    phase: string;
    port: number;
    spec_config: Record<'id', number>;
    status: string;
  }[];
  operations: Array<{
    cluster_id: number;
    flow_id: number;
    operator: string;
    status: PipelineStatus;
    ticket_id: number;
    ticket_type: string;
    title: string;
  }>;
  phase: string;
  phase_name: string;
  region: string;
  slave_domain: string;
  status: string;
  storages: Array<{
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    bk_instance_id: number;
    instance: string;
    ip: string;
    name: string;
    port: number;
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
      storage_spec: Array<{
        mount_point: string;
        size: number;
        type: string;
      }>;
    };
    status: string;
    phase: string;
  }>;
  update_at: string;
  updater: string;

  constructor(payload: SqlServerSingleCluster) {
    super(payload);
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.cluster_alias = payload.cluster_alias;
    this.cluster_name = payload.cluster_name;
    this.cluster_time_zone = payload.cluster_time_zone;
    this.cluster_type = payload.cluster_type;
    this.cluster_type_name = payload.cluster_type_name;
    this.creator = payload.creator;
    this.db_module_id = payload.db_module_id;
    this.db_module_name = payload.db_module_name;
    this.id = payload.id;
    this.major_version = payload.major_version;
    this.master_domain = payload.master_domain;
    this.masters = payload.masters;
    this.operations = payload.operations;
    this.phase = payload.phase;
    this.phase_name = payload.phase_name;
    this.region = payload.region;
    this.slave_domain = payload.slave_domain;
    this.status = payload.status;
    this.storages = payload.storages;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }

  get dbStatusConfigureObj() {
    const text = SqlServerSingleCluster.statusMap[this.status] || '--';
    const theme = SqlServerSingleCluster.themes[this.status] || 'danger';
    return {
      text,
      theme,
    };
  }

  get runningOperation() {
    const operateTicketTypes = Object.keys(SqlServerSingleCluster.operationTextMap);
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
    return SqlServerSingleCluster.operationTextMap[this.operationRunningStatus];
  }

  get operationStatusIcon() {
    return SqlServerSingleCluster.operationIconMap[this.operationRunningStatus];
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
      icon: SqlServerSingleCluster.operationIconMap[item.ticket_type],
      tip: SqlServerSingleCluster.operationTextMap[item.ticket_type],
      ticketId: item.ticket_id,
    }));
  }

  get isAbnormal() {
    return this.status === 'ABNORMAL';
  }

  get isOnline() {
    return this.phase === 'online';
  }
}
