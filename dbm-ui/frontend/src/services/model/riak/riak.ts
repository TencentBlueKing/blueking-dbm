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

import type { ClusterListEntry, ClusterListNode, ClusterListOperation } from '@services/types';

import { isRecentDays, utcDisplayTime } from '@utils';

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

  access_url: string;
  bk_biz_id: number;
  bk_biz_name: string;
  bk_cloud_id: number;
  bk_cloud_name: string;
  cluster_access_port: number;
  cluster_alias: string;
  cluster_entry: ClusterListEntry[];
  cluster_name: string;
  cluster_stats: Record<'used' | 'total' | 'in_use', number>;
  cluster_time_zone: string;
  cluster_type: string;
  cluster_type_name: string;
  create_at: string;
  creator: string;
  db_module_id: number;
  db_module_name: string;
  domain: string;
  id: number;
  major_version: string;
  master_domain: string;
  operations: ClusterListOperation[];
  permission: {
    riak_access_entry_view: boolean;
    riak_cluster_destroy: boolean;
    riak_cluster_migrate: boolean;
    riak_cluster_reboot: boolean;
    riak_cluster_scale_in: boolean;
    riak_cluster_scale_out: boolean;
    riak_enable_disable: boolean;
    riak_view: boolean;
  };
  phase: 'online' | 'offline';
  phase_name: string;
  region: string;
  riak_node: ClusterListNode[];
  slave_domain: string;
  status: 'normal' | 'abnormal';
  update_at: string;
  updater: string;

  constructor(payload = {} as Riak) {
    this.access_url = payload.access_url;
    this.bk_biz_id = payload.bk_biz_id || 0;
    this.bk_biz_name = payload.bk_biz_name || '';
    this.bk_cloud_id = payload.bk_cloud_id || 0;
    this.bk_cloud_name = payload.bk_cloud_name || '';
    this.cluster_access_port = payload.cluster_access_port;
    this.cluster_alias = payload.cluster_alias;
    this.cluster_entry = payload.cluster_entry || [];
    this.cluster_name = payload.cluster_name || '';
    this.cluster_stats = payload.cluster_stats || {};
    this.cluster_type = payload.cluster_type || '';
    this.cluster_type_name = payload.cluster_type_name || '';
    this.cluster_time_zone = payload.cluster_time_zone || '';
    this.create_at = payload.create_at || '';
    this.creator = payload.creator || '';
    this.db_module_id = payload.db_module_id || 0;
    this.db_module_name = payload.db_module_name || '';
    this.domain = payload.domain;
    this.id = payload.id || 0;
    this.master_domain = payload.master_domain || '';
    this.major_version = payload.major_version || '';
    this.operations = payload.operations || [];
    this.permission = payload.permission || {};
    this.phase = payload.phase || '';
    this.phase_name = payload.phase_name || '';
    this.region = payload.region || '';
    this.riak_node = payload.riak_node || [];
    this.slave_domain = payload.slave_domain || '';
    this.status = payload.status || '';
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }

  get isNewRow() {
    return isRecentDays(this.create_at, 24 * 3);
  }

  get allInstanceList() {
    return [...this.riak_node];
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

  get isOffline() {
    return this.phase === 'offline';
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
