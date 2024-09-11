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

import { PipelineStatus } from '@common/const';

import { t } from '@locales/index';

import TimeBaseClassModel from '../utils/time-base-class';

interface SqlServerHaInstance {
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
}

export default class SqlServerHaCluster extends TimeBaseClassModel {
  static SQLSERVER_DESTROY = 'SQLSERVER_DESTROY';
  static SQLSERVER_DISABLE = 'SQLSERVER_DISABLE';
  static SQLSERVER_ENABLE = 'SQLSERVER_ENABLE';
  static operationIconMap = {
    [SqlServerHaCluster.SQLSERVER_ENABLE]: t('启用中'),
    [SqlServerHaCluster.SQLSERVER_DISABLE]: t('禁用中'),
    [SqlServerHaCluster.SQLSERVER_DESTROY]: t('删除中'),
  };
  static operationTextMap = {
    [SqlServerHaCluster.SQLSERVER_DESTROY]: t('删除任务执行中'),
    [SqlServerHaCluster.SQLSERVER_DISABLE]: t('禁用任务执行中'),
    [SqlServerHaCluster.SQLSERVER_ENABLE]: t('启用任务执行中'),
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
  cluster_access_port: number;
  cluster_alias: string;
  cluster_entry: string[];
  cluster_name: string;
  cluster_stats: Record<'used' | 'total' | 'in_use', number>;
  cluster_time_zone: string;
  cluster_type: string;
  cluster_type_name: string;
  create_at: string;
  creator: string;
  db_module_id: number;
  db_module_name: string;
  id: number;
  major_version: string;
  master_domain: string;
  masters: SqlServerHaInstance[];
  operations: Array<{
    cluster_id: number;
    flow_id: number;
    operator: string;
    status: PipelineStatus;
    ticket_id: number;
    ticket_type: string;
    title: string;
  }>;
  permission: {
    access_entry_edit: boolean;
    sqlserver_view: boolean;
  };
  phase: string;
  phase_name: string;
  region: string;
  slave_domain: string;
  slaves: SqlServerHaInstance[];
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
  status: string;
  sync_mode: string;
  update_at: Date | string;
  updater: string;

  constructor(payload: SqlServerHaCluster) {
    super(payload);
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.cluster_access_port = payload.cluster_access_port;
    this.cluster_alias = payload.cluster_alias;
    this.cluster_entry = payload.cluster_entry || [];
    this.cluster_name = payload.cluster_name;
    this.cluster_time_zone = payload.cluster_time_zone;
    this.cluster_stats = payload.cluster_stats || {};
    this.cluster_type = payload.cluster_type;
    this.cluster_type_name = payload.cluster_type_name;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.db_module_id = payload.db_module_id;
    this.db_module_name = payload.db_module_name;
    this.id = payload.id;
    this.major_version = payload.major_version;
    this.master_domain = payload.master_domain;
    this.masters = payload.masters;
    this.operations = payload.operations;
    this.permission = payload.permission || {};
    this.phase = payload.phase;
    this.phase_name = payload.phase_name;
    this.region = payload.region;
    this.slave_domain = payload.slave_domain;
    this.slaves = payload.slaves;
    this.spec_config = payload.spec_config;
    this.status = payload.status;
    this.sync_mode = payload.sync_mode;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }

  get dbStatusConfigureObj() {
    const text = SqlServerHaCluster.statusMap[this.status] || '--';
    const theme = SqlServerHaCluster.themes[this.status] || 'danger';
    return {
      text,
      theme,
    };
  }

  get masterDomainDisplayName() {
    const port = this.masters[0]?.port;
    const displayName = port ? `${this.master_domain}:${port}` : this.master_domain;
    return displayName;
  }

  get slaveDomainDisplayName() {
    const port = this.slaves[0]?.port;
    const displayName = port ? `${this.slave_domain}:${port}` : this.slave_domain;
    return this.slave_domain ? displayName : '--';
  }

  get allInstanceList() {
    return [...this.masters, ...this.slaves];
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
    const operateTicketTypes = Object.keys(SqlServerHaCluster.operationTextMap);
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
    return SqlServerHaCluster.operationTextMap[this.operationRunningStatus];
  }

  get operationStatusIcon() {
    return SqlServerHaCluster.operationIconMap[this.operationRunningStatus];
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
      icon: SqlServerHaCluster.operationIconMap[item.ticket_type],
      tip: SqlServerHaCluster.operationTextMap[item.ticket_type],
      ticketId: item.ticket_id,
    }));
  }

  get isAbnormal() {
    return this.status === 'abnormal';
  }

  get isOnline() {
    return this.phase === 'online';
  }

  get isOffline() {
    return this.phase === 'offline';
  }

  get isStarting() {
    return Boolean(this.operations.find((item) => item.ticket_type === SqlServerHaCluster.SQLSERVER_ENABLE));
  }
}
