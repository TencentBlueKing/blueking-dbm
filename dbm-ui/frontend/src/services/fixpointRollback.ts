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

// import BackupLogModel from '@services/model/fixpoint-rollback/backup-log';

import http from './http';

// 通过下发脚本到机器获取集群备份记录
export const executeBackupLogScript = function (params: {bk_biz_id: number, cluster_id: number}):
Promise<number> {
  return http.get(`/apis/mysql/bizs/${params.bk_biz_id}/fixpoint_rollback/execute_backup_log_script/`, params);
};

// 通过日志平台获取集群备份记录
export const queryBackupLogFromBklog = function (params: { bk_biz_id: number, cluster_id: number}):
Promise<any[]> {
  return http.get(`/apis/mysql/bizs/${params.bk_biz_id}/fixpoint_rollback/query_backup_log_from_bklog/`, params);
  // .then(data => data.map((item: BackupLogModel) => new BackupLogModel(item)));
};

// 根据job id查询任务执行状态和执行结果
export const queryBackupLogJob = function (params: { bk_biz_id: number, cluster_id: number, job_instance_id: number}):
Promise<{
  backup_logs: Array<any>,
  job_status: string,
  message: string
}> {
  return http.get(`/apis/mysql/bizs/${params.bk_biz_id}/fixpoint_rollback/query_backup_log_job/`, params);
};
