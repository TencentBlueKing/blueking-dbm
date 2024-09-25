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

import type { HostInfo, InstanceListOperation, InstanceRelatedCluster } from '@services/types';

import { t } from '@locales/index';

export default class HdfsInstance {
  static HDFS_REBOOT = 'HDFS_REBOOT';

  static operationIconMap = {
    [HdfsInstance.HDFS_REBOOT]: 'zhongqizhong',
  };

  static operationTextMap = {
    [HdfsInstance.HDFS_REBOOT]: t('重启任务进行中'),
  };

  bk_cloud_id: number;
  bk_host_id: number;
  cluster_id: number;
  create_at: string;
  domain: string;
  host_info: HostInfo;
  id: number;
  instance_address: string;
  instance_name: string;
  operations: InstanceListOperation[];
  restart_at: string;
  related_clusters: InstanceRelatedCluster[];
  role: string;
  status: string;

  constructor(payload = {} as HdfsInstance) {
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_host_id = payload.bk_host_id;
    this.cluster_id = payload.cluster_id;
    this.create_at = payload.create_at;

    this.domain = payload.domain;
    this.host_info = payload.host_info || {};
    this.id = payload.id;
    this.instance_address = payload.instance_address;
    this.instance_name = payload.instance_name;
    this.operations = payload.operations || [];
    this.related_clusters = payload.related_clusters || [];
    this.restart_at = payload.restart_at;
    this.role = payload.role;
    this.status = payload.status;
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
    return HdfsInstance.operationTextMap[this.operationRunningStatus];
  }
  // 操作中的状态 icon
  get operationStatusIcon() {
    return HdfsInstance.operationIconMap[this.operationRunningStatus];
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
    // 各个操作互斥，有其他任务进行中禁用操作按钮
    if (this.operationRunningStatus) {
      return true;
    }
    return false;
  }

  get operationTagTips() {
    return this.operations.map((item) => ({
      icon: HdfsInstance.operationIconMap[item.ticket_type],
      tip: HdfsInstance.operationTextMap[item.ticket_type],
      ticketId: item.ticket_id,
    }));
  }
}
