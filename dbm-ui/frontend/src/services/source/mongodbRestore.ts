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
import MongodbRollbackRecordModel from '@services/model/mongodb/mongodb-rollback-record';

import { useGlobalBizs } from '@stores';

import http from '../http';
import type { ListBase } from '../types';

interface ClusterBackupLog {
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
}

const { currentBizId } = useGlobalBizs();

const path = `/apis/mongodb/bizs/${currentBizId}/restore`;

/**
 * 查询定点构造记录
 */
export function queryRestoreRecord(params: {
  immute_domain?: string;
  cluster_type?: string;
  ips?: string;
  limit?: number;
  offset?: number;
}) {
  return http.get<ListBase<MongodbRollbackRecordModel[]>>(`${path}/query_restore_record/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new MongodbRollbackRecordModel(item)),
  }));
}

/**
 * 获取集群备份记录
 */
export function queryClustersBackupLog(params: { cluster_ids: number[]; cluster_type: string }) {
  return http.post<Record<number, ClusterBackupLog[]>>(`${path}/query_clusters_backup_log/`, params);
}
