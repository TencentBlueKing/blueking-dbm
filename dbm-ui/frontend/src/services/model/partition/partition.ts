/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited; a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing; software distributed under the License is distributed
 * on an "AS IS" BASIS; WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND; either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */
import { isRecentDays, utcDisplayTime } from '@utils';

const STATUS_FAILED = 'FAILED';
const STATUS_SUCCESS = 'SUCCESS';
const STATUS_NO_EXECUTION_RECORD = 'NO_EXECUTION_RECORD';

export default class Partition {
  static STATUS_FAILED = STATUS_FAILED;
  static STATUS_NO_EXECUTION_RECORD = STATUS_NO_EXECUTION_RECORD;
  static STATUS_SUCCESS = STATUS_SUCCESS;

  bk_biz_id: number;
  bk_cloud_id: number;
  check_info: string;
  cluster_id: number;
  create_time: string;
  creator: string;
  dblike: string;
  execute_time: string;
  expire_time: number;
  extra_partition: number;
  id: number;
  immute_domain: string;
  partition_column: string;
  partition_column_type: string;
  partition_time_interval: number;
  partition_type: number;
  permission: {
    mysql_partition: boolean;
    mysql_partition_create: boolean;
    mysql_partition_delete: boolean;
    mysql_partition_enable_disable: boolean;
    // 聚合权限（灰度期可选，缺省 false）
    mysql_partition_manage?: boolean;
    mysql_partition_update: boolean;
    tendb_partition_enable_disable: boolean;
    tendbcluster_partition_manage: boolean;
  };
  phase: string;
  port: number;
  reserved_partition: number;
  status: string;
  tblike: string;
  ticket_id: number;
  ticket_status: string;
  time_zone: string;
  update_time: string;
  updator: string;

  constructor(payload = {} as Partition) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.check_info = payload.check_info;
    this.cluster_id = payload.cluster_id;
    this.create_time = payload.create_time;
    this.creator = payload.creator;
    this.dblike = payload.dblike;
    this.execute_time = payload.execute_time;
    this.expire_time = payload.expire_time;
    this.extra_partition = payload.extra_partition;
    this.id = payload.id;
    this.immute_domain = payload.immute_domain;
    this.partition_column_type = payload.partition_column_type;
    this.partition_column = payload.partition_column;
    this.partition_time_interval = payload.partition_time_interval;
    this.partition_type = payload.partition_type;
    this.permission = payload.permission || {};
    this.phase = payload.phase;
    this.port = payload.port;
    this.time_zone = payload.time_zone;
    this.reserved_partition = payload.reserved_partition;
    this.status = payload.status;
    this.tblike = payload.tblike;
    this.ticket_id = payload.ticket_id;
    this.ticket_status = payload.ticket_status;
    this.update_time = payload.update_time;
    this.updator = payload.updator;
  }

  get executeTimeDisplay() {
    return utcDisplayTime(this.execute_time);
  }

  get isFailed() {
    return this.status === Partition.STATUS_FAILED;
  }

  get isFinished() {
    return this.status === Partition.STATUS_SUCCESS;
  }

  get isNew() {
    return isRecentDays(this.create_time, 24 * 3);
  }

  get isOffline() {
    return this.phase === 'offline';
  }

  get isOnline() {
    return this.phase === 'online';
  }

  get statusIcon() {
    const iconMap = {
      [Partition.STATUS_FAILED]: 'sync-failed',
      [Partition.STATUS_NO_EXECUTION_RECORD]: 'sync-default',
      [Partition.STATUS_SUCCESS]: 'sync-success',
    };

    return iconMap[this.status] || '';
  }

  get statusText() {
    const statusMap = {
      [Partition.STATUS_FAILED]: '执行失败',
      [Partition.STATUS_NO_EXECUTION_RECORD]: '无执行记录',
      [Partition.STATUS_SUCCESS]: '执行成功',
    };
    return statusMap[this.status] || '--';
  }
}
