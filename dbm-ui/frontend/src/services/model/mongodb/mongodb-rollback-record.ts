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
import { utcDisplayTime } from '@utils';

import { t } from '@locales/index';

interface ClusterInfo {
  access_port: number;
  bk_cloud_id: number;
  cluster_type: string;
  id: number;
  immute_domain: string;
  major_version: string;
  name: string;
  operations: {
    cluster_id: number;
    flow_id: number;
    operator: string;
    status: string;
    ticket_id: number;
    ticket_type: string;
    title: string;
  }[];
  region: string;
}

export default class MongodbRollbackRecord {
  static MongoShardedCluster = 'MongoShardedCluster'; // 分片集群
  static MongoReplicaSet = 'MongoReplicaSet'; // 副本集集群

  static MONGODB_TEMPORARY_DESTROY = 'MONGODB_TEMPORARY_DESTROY';

  static operationIconMap = {
    [MongodbRollbackRecord.MONGODB_TEMPORARY_DESTROY]: t('销毁中'), 
  };

  static operationTextMap = {
    [MongodbRollbackRecord.MONGODB_TEMPORARY_DESTROY]: t('销毁任务进行中'),
  };

  backupinfo: {
    app: string;
    app_name: string;
    bk_biz_id: number;
    bk_cloud_id: number;
    bs_status: string;
    bs_tag: string;
    bs_taskid: string;
    cluster_domain: string;
    cluster_id: number;
    cluster_name: string;
    cluster_type: string;
    end_time: string;
    file_name: string;
    file_path: string;
    file_size: number;
    meta_role: string;
    my_file_num: number;
    pitr_binlog_index: number;
    pitr_date: string;
    pitr_file_type: string;
    pitr_fullname: string;
    pitr_last_pos: number;
    releate_bill_id: string;
    releate_bill_info: string;
    report_type: string;
    role_type: string;
    server_ip: string;
    server_port: number;
    set_name: string;
    src: string;
    start_time: string;
    total_file_num: number;
  };
  instance_per_host: number;
  ns_filter: {
    db_patterns: string[];
    ignore_dbs: string[];
    table_patterns: string[];
    ignore_tables: string[];
  };
  record_id: number;
  rollback_time: string;
  source_cluster: ClusterInfo;
  target_cluster: ClusterInfo;
  target_cluster_id: number;
  target_nodes: string[];
  ticket_id: number;

  constructor(payload = {} as MongodbRollbackRecord) {
    this.backupinfo = payload.backupinfo;
    this.instance_per_host = payload.instance_per_host;
    this.ns_filter = payload.ns_filter;
    this.record_id = payload.record_id;
    this.rollback_time = payload.rollback_time;
    this.source_cluster = payload.source_cluster;
    this.target_cluster = payload.target_cluster;
    this.target_cluster_id = payload.target_cluster_id;
    this.target_nodes = payload.target_nodes;
    this.ticket_id = payload.ticket_id;
  }

  get runningOperation() {
    return this.target_cluster.operations.find(item => item.ticket_type in MongodbRollbackRecord.operationTextMap);
  }

  // 操作中的状态
  get operationRunningStatus() {
    if (this.target_cluster.operations.length < 1) {
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
    return MongodbRollbackRecord.operationTextMap[this.operationRunningStatus];
  }

  // 操作中的状态 icon
  get operationStatusIcon() {
    return MongodbRollbackRecord.operationIconMap[this.operationRunningStatus];
  }

  // 操作中的单据 ID
  get operationTicketId() {
    if (this.target_cluster.operations.length < 1) {
      return 0;
    }
    const operation = this.runningOperation;
    if (!operation) {
      return 0;
    }
    return operation.ticket_id;
  }

  get operationDisabled() {
    // 各个操作互斥，有其他任务进行中禁用操作按钮
    if (this.operationTicketId) {
      return true;
    }
    return false;
  }

  get operationTagTips() {
    return this.target_cluster.operations.map(item => ({
      icon: MongodbRollbackRecord.operationIconMap[item.ticket_type],
      tip: MongodbRollbackRecord.operationTextMap[item.ticket_type],
      ticketId: item.ticket_id,
    }));
  }

  get sourceClusteText() {
    return `${this.source_cluster.immute_domain}:${this.source_cluster.access_port}`;
  }

  get sourceClusterTypeText() {
    return this.source_cluster.cluster_type === MongodbRollbackRecord.MongoShardedCluster ? t('分片') : t('副本集');
  }

  get rollbackTypeText() {
    if (this.rollback_time) {
      return `${t('回档到指定时间')}（${utcDisplayTime(this.rollback_time)}）`;
    }
    return `${t('备份记录')}（${this.backupinfo.role_type}${utcDisplayTime(this.backupinfo.end_time)}）`;
  }
}
