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

import type { ClusterListEntry, ClusterListNode, ClusterListSpec } from '@services/types';

import { ClusterAffinityMap, ClusterTypes } from '@common/const';

import { t } from '@locales/index';

import ClusterBase from '../_clusterBase';

const STATUS_NORMAL = 'normal';
const STATUS_ABNORMAL = 'abnormal';

export default class Pulsar extends ClusterBase {
  static STATUS_NORMAL = STATUS_NORMAL;
  static STATUS_ABNORMAL = STATUS_ABNORMAL;

  static PULSAR_SCALE_UP = 'PULSAR_SCALE_UP';
  static PULSAR_SHRINK = 'PULSAR_SHRINK';
  static PULSAR_REPLACE = 'PULSAR_REPLACE';
  static PULSAR_ENABLE = 'PULSAR_ENABLE';
  static PULSAR_DISABLE = 'PULSAR_DISABLE';
  static PULSAR_DESTROY = 'PULSAR_DESTROY';
  static PULSAR_REBOOT = 'PULSAR_REBOOT';

  static operationIconMap = {
    [Pulsar.PULSAR_SCALE_UP]: t('扩容中'),
    [Pulsar.PULSAR_SHRINK]: t('缩容中'),
    [Pulsar.PULSAR_REPLACE]: t('替换中'),
    [Pulsar.PULSAR_ENABLE]: t('启用中'),
    [Pulsar.PULSAR_DISABLE]: t('禁用中'),
    [Pulsar.PULSAR_DESTROY]: t('删除中'),
    [Pulsar.PULSAR_REBOOT]: t('重启中'),
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
  cluster_entry: ClusterListEntry[];
  cluster_name: string;
  cluster_spec: ClusterListSpec;
  cluster_stats: Record<'used' | 'total' | 'in_use', number>;
  cluster_type: ClusterTypes;
  cluster_type_name: string;
  cluster_time_zone: string;
  create_at: string;
  creator: string;
  disaster_tolerance_level: keyof typeof ClusterAffinityMap;
  domain: string;
  id: number;
  major_version: string;
  operations: Array<{
    cluster_id: number;
    flow_id: number;
    status: string;
    ticket_id: number;
    ticket_type: string;
    title: string;
  }>;
  phase: string;
  pulsar_bookkeeper: ClusterListNode[];
  pulsar_broker: ClusterListNode[];
  pulsar_zookeeper: ClusterListNode[];
  permission: {
    access_entry_edit: boolean;
    pulsar_access_entry_view: boolean;
    pulsar_view: boolean;
    pulsar_enable_disable: boolean;
    pulsar_destroy: boolean;
    pulsar_scale_up: boolean;
    pulsar_shrink: boolean;
    pulsar_replace: boolean;
    pulsar_reboot: boolean;
  };
  region: string;
  status: string;
  update_at: string;
  updater: string;

  constructor(payload = {} as Pulsar) {
    super(payload);
    this.access_url = payload.access_url;
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.cap_usage = payload.cap_usage;
    this.cluster_alias = payload.cluster_alias;
    this.cluster_entry = payload.cluster_entry;
    this.cluster_name = payload.cluster_name;
    this.cluster_spec = payload.cluster_spec || {};
    this.cluster_stats = payload.cluster_stats || {};
    this.cluster_type = payload.cluster_type;
    this.cluster_type_name = payload.cluster_type_name;
    this.cluster_time_zone = payload.cluster_time_zone;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.disaster_tolerance_level = payload.disaster_tolerance_level;
    this.domain = payload.domain;
    this.id = payload.id;
    this.major_version = payload.major_version;
    this.operations = payload.operations || [];
    this.phase = payload.phase;
    this.pulsar_bookkeeper = payload.pulsar_bookkeeper || [];
    this.pulsar_broker = payload.pulsar_broker || [];
    this.pulsar_zookeeper = payload.pulsar_zookeeper || [];
    this.permission = payload.permission || {};
    this.region = payload.region;
    this.status = payload.status;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }

  get runningOperation() {
    const operateTicketTypes = Object.keys(Pulsar.operationTextMap);
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
    const operation = this.runningOperation;
    if (!operation) {
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
    if (this.operationTicketId) {
      return true;
    }
    return false;
  }

  get masterDomainDisplayName() {
    const port = this.pulsar_broker[0]?.port;
    const displayName = port ? `${this.domain}:${port}` : this.domain;
    return displayName;
  }

  get allInstanceList() {
    return [...this.pulsar_bookkeeper, ...this.pulsar_broker, ...this.pulsar_zookeeper];
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

  get operationTagTips() {
    return this.operations.map((item) => ({
      icon: Pulsar.operationIconMap[item.ticket_type],
      tip: Pulsar.operationTextMap[item.ticket_type],
      ticketId: item.ticket_id,
    }));
  }

  get isStarting() {
    return Boolean(this.operations.find((item) => item.ticket_type === Pulsar.PULSAR_ENABLE));
  }

  get disasterToleranceLevelName() {
    return ClusterAffinityMap[this.disaster_tolerance_level];
  }

  get roleFailedInstanceInfo() {
    return {
      Bookkeeper: ClusterBase.getRoleFaildInstanceList(this.pulsar_bookkeeper),
      Zookeeper: ClusterBase.getRoleFaildInstanceList(this.pulsar_zookeeper),
      Broker: ClusterBase.getRoleFaildInstanceList(this.pulsar_broker),
    };
  }
}
