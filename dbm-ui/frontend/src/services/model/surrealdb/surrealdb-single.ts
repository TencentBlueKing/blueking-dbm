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

import type { ClusterListEntry, ClusterListOperation, ClusterListSpec } from '@services/types';

import { Affinity, affinityMap, ClusterTypes, TicketTypes } from '@common/const';

import { t } from '@locales/index';

import ClusterBase from '../_clusterBase';

export default class SurrealdbSingle extends ClusterBase {
  static operationIconMap: Record<string, string> = {
    [TicketTypes.K8S_SURREALDB_DELETE]: t('删除中'),
    [TicketTypes.K8S_SURREALDB_DISABLE]: t('禁用中'),
    [TicketTypes.K8S_SURREALDB_ENABLE]: t('启用中'),
    [TicketTypes.K8S_SURREALDB_RESTART]: t('重启中'),
  };

  static operationTextMap: Record<string, string> = {
    [TicketTypes.K8S_SURREALDB_DELETE]: t('删除任务进行中'),
    [TicketTypes.K8S_SURREALDB_DISABLE]: t('禁用任务进行中'),
    [TicketTypes.K8S_SURREALDB_ENABLE]: t('启用任务进行中'),
    [TicketTypes.K8S_SURREALDB_RESTART]: t('重启任务进行中'),
  };

  access_url: string;
  bk_biz_id: number;
  bk_biz_name: string;
  bk_cloud_id: number;
  bk_cloud_name: string;
  cluster_access_port: number;
  cluster_alias: string;
  cluster_entry: ClusterListEntry[];
  cluster_name: string;
  cluster_spec: ClusterListSpec;
  cluster_stats: Record<'used' | 'total' | 'in_use', number>;
  cluster_time_zone: string;
  cluster_type: ClusterTypes;
  cluster_type_name: string;
  components: {
    alias: string;
    description: string;
    name: string;
  }[];
  create_at: string;
  creator: string;
  db_module_id: number;
  db_module_name: string;
  disaster_tolerance_level: Affinity;
  dns_to_clb: boolean;
  domain: string;
  id: number;
  k8s_cluster_name: string;
  major_version: string;
  master_domain: string;
  namespace: string;
  operations: ClusterListOperation[];
  permission: {
    k8s_surrealdb_destroy: boolean;
    k8s_surrealdb_edit: boolean;
    k8s_surrealdb_enable_disable: boolean;
    k8s_surrealdb_manage: boolean;
    k8s_surrealdb_view: boolean;
  };
  phase: 'online' | 'offline';
  phase_name: string;
  status: 'normal' | 'abnormal';
  update_at: string;
  updater: string;

  constructor(payload = {} as SurrealdbSingle) {
    super(payload);
    this.access_url = payload.access_url;
    this.bk_biz_id = payload.bk_biz_id || 0;
    this.bk_biz_name = payload.bk_biz_name || '';
    this.bk_cloud_id = payload.bk_cloud_id || 0;
    this.bk_cloud_name = payload.bk_cloud_name || '';
    this.cluster_access_port = payload.cluster_access_port;
    this.cluster_alias = payload.cluster_alias;
    this.cluster_entry = payload.cluster_entry || [];
    this.cluster_name = payload.cluster_name || '';
    this.cluster_spec = payload.cluster_spec || {};
    this.cluster_stats = payload.cluster_stats || {};
    this.cluster_type = payload.cluster_type || '';
    this.cluster_type_name = payload.cluster_type_name || '';
    this.cluster_time_zone = payload.cluster_time_zone || '';
    this.components = payload.components || [];
    this.create_at = payload.create_at || '';
    this.creator = payload.creator || '';
    this.db_module_id = payload.db_module_id || 0;
    this.db_module_name = payload.db_module_name || '';
    this.disaster_tolerance_level = payload.disaster_tolerance_level;
    this.dns_to_clb = payload.dns_to_clb;
    this.domain = payload.domain;
    this.id = payload.id || 0;
    this.k8s_cluster_name = payload.k8s_cluster_name;
    this.master_domain = payload.master_domain || '';
    this.major_version = payload.major_version || '';
    this.namespace = payload.namespace;
    this.operations = payload.operations || [];
    this.permission = payload.permission || {};
    this.phase = payload.phase || '';
    this.phase_name = payload.phase_name || '';
    this.status = payload.status || '';
    this.update_at = payload.update_at || '';
    this.updater = payload.updater;
  }

  get disasterToleranceLevelName() {
    return affinityMap[this.disaster_tolerance_level];
  }

  get isClusterNormal() {
    return this.status === 'normal';
  }

  get isDisabled() {
    return !this.isOnline && !this.isOfflineOperationRunning;
  }

  get isOfflineOperationRunning() {
    return ([TicketTypes.K8S_SURREALDB_ENABLE, TicketTypes.K8S_SURREALDB_DELETE] as string[]).includes(
      this.operationRunningStatus,
    );
  }

  get isOnlineCLB() {
    return this.cluster_entry.some((item) => item.cluster_entry_type === 'clbDns');
  }

  get isStarting() {
    return Boolean(this.operations.find((item) => item.ticket_type === TicketTypes.K8S_SURREALDB_ENABLE));
  }

  get masterDomain() {
    return this.masterDomainDisplayName;
  }

  get masterDomainDisplayName() {
    const domainItem = this.cluster_entry.find((item) => item.cluster_entry_type === 'clbDns');
    const displayName = domainItem?.entry || '';
    return `${displayName}:${this.cluster_access_port}`;
  }

  get operationDisabled() {
    if (!this.isClusterNormal) {
      return true;
    }

    if (this.operationTicketId) {
      return true;
    }
    return false;
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

  get operationStatusIcon() {
    return SurrealdbSingle.operationIconMap[this.operationRunningStatus];
  }

  get operationStatusText() {
    return SurrealdbSingle.operationTextMap[this.operationRunningStatus];
  }

  get operationTagTips() {
    return this.operations.map((item) => ({
      icon: SurrealdbSingle.operationIconMap[item.ticket_type],
      ticketId: item.ticket_id,
      tip: SurrealdbSingle.operationTextMap[item.ticket_type],
    }));
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

  get roleFailedInstanceInfo() {
    return {
      Surreal: [],
    };
  }

  get runningOperation() {
    const operateTicketTypes = Object.keys(SurrealdbSingle.operationTextMap);
    return this.operations.find((item) => operateTicketTypes.includes(item.ticket_type) && item.status === 'RUNNING');
  }
}
