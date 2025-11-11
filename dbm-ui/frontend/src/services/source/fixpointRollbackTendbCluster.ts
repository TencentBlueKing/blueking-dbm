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

import FixpointLogModel from '@services/model/fixpoint-rollback/fixpoint-log';
import type { ListBase } from '@services/types';

import { useGlobalBizs } from '@stores';

import http from '../http';
import BackupLogRecordModel from '@services/model/tendbcluster/backup-log-record';

const { currentBizId } = useGlobalBizs();

const path = `/apis/mysql/bizs/${currentBizId}/fixpoint_rollback`;

/**
 * 通过日志平台获取集群备份记录
 */
export function queryBackupLogFromBklog(params: { cluster_id: number; limit?: number }) {
  return http.get<BackupLogRecordModel[]>(`${path}/query_backup_log_from_bklog/`, params);
}

/**
 * 根据job id查询任务执行状态和执行结果
 */
export function queryBackupLogFromLoacal(params: { cluster_id: number; limit?: number }) {
  return http.get<BackupLogRecordModel[]>(`${path}/query_backup_log_from_local/`, params);
}

/**
 * 获取集群列表
 */
export function queryFixpointLog(params: { cluster_id: number; job_instance_id: number; rollback_time: string }) {
  return http.get<ListBase<FixpointLogModel[]>>(`${path}/query_fixpoint_log/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new FixpointLogModel(item)),
  }));
}

/**
 * 获取定点构造记录
 */
export function queryLatesBackupLog(params: {
  bk_biz_id: number;
  cluster_id: number;
  job_instance_id?: number;
  rollback_time: string;
  backup_source?: string;
  backup_method?: string;
}) {
  return http.get<BackupLogRecordModel>(`${path}/query_latest_backup_log/`, params);
}

/**
 * 获取最近备份记录
 */
export function queryLatestTimeBackupLog(params: {
  bk_biz_id: number;
  cluster_id: number;
  deadlines_days?: number;
  latest_time?: string;
  backup_source?: string;
  backup_method?: string;
  limit?: number;
  offset?: number;
  is_full_backup?: boolean;
}) {
  return http.get<BackupLogRecordModel>(`${path}/latest_time_backup_log/`, params);
}

/**
 * 获取集群备份记录
 */
export function queryBackupLogFromHandler(params: {
  cluster_id: number;
  limit?: number;
  offset?: number;
  deadlines_days?: number; //指定备份天数前数据
  latest_time?: string; //备份最迟时间
  backup_method?: string; //过滤备份类型
  is_full_backup?: boolean; //是否为全备
  backup_source?: string; //备份源
}) {
  return http.get<Record<string, BackupLogRecordModel>>(`${path}/query_backup_log_from_handler/`, params);
}
