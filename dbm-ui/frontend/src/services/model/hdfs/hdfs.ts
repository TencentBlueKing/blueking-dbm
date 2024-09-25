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

import { utcDisplayTime } from '@utils';

import { t } from '@locales/index';

// const STATUS_NORMAL = 'normal';
const STATUS_ABNORMAL = 'abnormal';

export default class Hdfs {
  static HDFS_SCALE_UP = 'HDFS_SCALE_UP';
  static HDFS_SHRINK = 'HDFS_SHRINK';
  static HDFS_REPLACE = 'HDFS_REPLACE';
  static HDFS_ENABLE = 'HDFS_ENABLE';
  static HDFS_DISABLE = 'HDFS_DISABLE';
  static HDFS_DESTROY = 'HDFS_DESTROY';
  static HDFS_REBOOT = 'HDFS_REBOOT';

  static operationIconMap = {
    [Hdfs.HDFS_SCALE_UP]: 'kuorongzhong',
    [Hdfs.HDFS_SHRINK]: 'suorongzhong',
    [Hdfs.HDFS_REPLACE]: 'tihuanzong',
    [Hdfs.HDFS_ENABLE]: 'qiyongzhong',
    [Hdfs.HDFS_DISABLE]: 'jinyongzhong',
    [Hdfs.HDFS_DESTROY]: 'shanchuzhong',
    [Hdfs.HDFS_REBOOT]: 'zhongqizhong',
  };

  static operationTextMap = {
    [Hdfs.HDFS_SCALE_UP]: t('扩容任务进行中'),
    [Hdfs.HDFS_SHRINK]: t('缩容任务进行中'),
    [Hdfs.HDFS_REPLACE]: t('替换任务进行中'),
    [Hdfs.HDFS_ENABLE]: t('启用任务进行中'),
    [Hdfs.HDFS_DISABLE]: t('禁用任务进行中'),
    [Hdfs.HDFS_DESTROY]: t('删除任务进行中'),
    [Hdfs.HDFS_REBOOT]: t('实例重启任务进行中'),
  };

  access_url: string;
  bk_biz_id: number;
  bk_biz_name: string;
  bk_cloud_id: number;
  bk_cloud_name: string;
  cluster_access_port: number;
  cluster_alias: string;
  cluster_entry: ClusterListEntry;
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
  hdfs_datanode: Array<ClusterListNode>;
  hdfs_journalnode: Array<ClusterListNode>;
  hdfs_namenode: Array<ClusterListNode>;
  hdfs_zookeeper: Array<ClusterListNode>;
  id: number;
  major_version: string;
  master_domain: string;
  operations: ClusterListOperation[];
  permission: {
    access_entry_edit: boolean;
    hdfs_access_entry_view: boolean;
    hdfs_view: boolean;
    hdfs_enable_disable: boolean;
    hdfs_destroy: boolean;
    hdfs_scale_up: boolean;
    hdfs_shrink: boolean;
    hdfs_replace: boolean;
    hdfs_reboot: boolean;
  };
  phase: string;
  region: string;
  slave_domain: string;
  status: string;
  update_at: string;
  updater: string;

  constructor(payload = {} as Hdfs) {
    this.access_url = payload.access_url;
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.cluster_access_port = payload.cluster_access_port;
    this.cluster_alias = payload.cluster_alias;
    this.cluster_entry = payload.cluster_entry;
    this.cluster_name = payload.cluster_name;
    this.cluster_stats = payload.cluster_stats || {};
    this.cluster_type = payload.cluster_type;
    this.cluster_type_name = payload.cluster_type_name;
    this.cluster_time_zone = payload.cluster_time_zone;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.db_module_id = payload.db_module_id;
    this.db_module_name = payload.db_module_name;
    this.domain = payload.domain;
    this.hdfs_datanode = payload.hdfs_datanode;
    this.hdfs_journalnode = payload.hdfs_journalnode;
    this.hdfs_namenode = payload.hdfs_namenode;
    this.hdfs_zookeeper = payload.hdfs_zookeeper;
    this.id = payload.id;
    this.major_version = payload.major_version;
    this.master_domain = payload.master_domain;
    this.permission = payload.permission || {};
    this.phase = payload.phase;
    this.region = payload.region;
    this.slave_domain = payload.slave_domain;
    this.status = payload.status;
    this.update_at = payload.update_at;
    this.updater = payload.updater;

    this.operations = this.initOperations(payload.operations);
  }

  get allInstanceList() {
    return [...this.hdfs_datanode, ...this.hdfs_journalnode, ...this.hdfs_namenode, ...this.hdfs_zookeeper];
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
    const operateTicketTypes = Object.keys(Hdfs.operationTextMap);
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
    return Hdfs.operationTextMap[this.operationRunningStatus];
  }
  // 操作中的状态 icon
  get operationStatusIcon() {
    return Hdfs.operationIconMap[this.operationRunningStatus];
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

  get isOnline() {
    return this.phase === 'online';
  }

  get isOffline() {
    return this.phase === 'offline';
  }

  get domainDisplayName() {
    const port = this.hdfs_namenode[0]?.port;
    const displayName = port ? `${this.domain}:${port}` : this.domain;
    return displayName;
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }

  get operationTagTips() {
    return this.operations.map((item) => ({
      icon: Hdfs.operationIconMap[item.ticket_type],
      tip: Hdfs.operationTextMap[item.ticket_type],
      ticketId: item.ticket_id,
    }));
  }

  initOperations(payload = [] as Hdfs['operations']) {
    if (!Array.isArray(payload)) {
      return [];
    }

    return payload;
  }

  get isStarting() {
    return Boolean(this.operations.find((item) => item.ticket_type === Hdfs.HDFS_ENABLE));
  }
}
