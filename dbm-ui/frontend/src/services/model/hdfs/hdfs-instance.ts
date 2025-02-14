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

import type { HostInfo, InstanceListOperation, InstanceListSpecConfig, InstanceRelatedCluster } from '@services/types';

import { ClusterTypes } from '@common/const';

import { t } from '@locales/index';

export default class HdfsInstance {
  static HDFS_REBOOT = 'HDFS_REBOOT';

  static operationIconMap = {
    [HdfsInstance.HDFS_REBOOT]: t('重启中'),
  };

  static operationTextMap = {
    [HdfsInstance.HDFS_REBOOT]: t('重启任务进行中'),
  };

  bk_cloud_id: number;
  bk_cloud_name: string;
  bk_host_id: number;
  bk_os_name: string;
  bk_rack_id: number;
  bk_sub_zone: string;
  bk_sub_zone_id: number;
  bk_svr_device_cls_name: string;
  cluster_id: number;
  cluster_name: string;
  cluster_type: ClusterTypes;
  cluster_type_name: string;
  create_at: string;
  db_module_id: number;
  db_module_name: string;
  host_info: HostInfo;
  id: number;
  instance_address: string;
  instance_name: string;
  ip: string;
  machine_type: string;
  master_domain: string;
  operations: InstanceListOperation[];
  permission: {
    hdfs_view: boolean;
  };
  port: number;
  restart_at: string;
  related_clusters: InstanceRelatedCluster[];
  role: string;
  slave_domain: string;
  spec_config: InstanceListSpecConfig;
  status: string;
  version: string;

  constructor(payload = {} as HdfsInstance) {
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.bk_host_id = payload.bk_host_id;
    this.bk_os_name = payload.bk_os_name;
    this.bk_rack_id = payload.bk_rack_id;
    this.bk_sub_zone = payload.bk_sub_zone;
    this.bk_sub_zone_id = payload.bk_sub_zone_id;
    this.bk_svr_device_cls_name = payload.bk_svr_device_cls_name;
    this.cluster_id = payload.cluster_id;
    this.cluster_name = payload.cluster_name;
    this.cluster_type = payload.cluster_type;
    this.cluster_type_name = payload.cluster_type_name;
    this.create_at = payload.create_at;
    this.db_module_id = payload.db_module_id;
    this.db_module_name = payload.db_module_name;
    this.host_info = payload.host_info || {};
    this.id = payload.id;
    this.instance_address = payload.instance_address;
    this.instance_name = payload.instance_name;
    this.ip = payload.ip;
    this.machine_type = payload.machine_type;
    this.master_domain = payload.master_domain;
    this.operations = payload.operations || [];
    this.permission = payload.permission;
    this.port = payload.port;
    this.restart_at = payload.restart_at;
    this.related_clusters = payload.related_clusters || [];
    this.role = payload.role;
    this.slave_domain = payload.slave_domain;
    this.spec_config = payload.spec_config || {};
    this.status = payload.status;
    this.version = payload.version;
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
