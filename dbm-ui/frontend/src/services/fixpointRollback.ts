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

import { useGlobalBizs } from '@stores';

import http from './http';
import type { ListBase } from './types';

// 通过日志平台获取集群备份记录
export const queryBackupLogFromBklog = function (params: { cluster_id: number }) {
  const { currentBizId } = useGlobalBizs();

  return http.get<
    {
      backup_id: string;
      backup_time: string;
      mysql_role: string;
    }[]
  >(`/apis/mysql/bizs/${currentBizId}/fixpoint_rollback/query_backup_log_from_bklog/`, params);
};

// 查询小于回档时间点最近的备份记录
export const queryLatesBackupLog = function (params: {
  bk_biz_id: number;
  cluster_id: number;
  rollback_time: string;
  job_instance_id: number;
}) {
  const { currentBizId } = useGlobalBizs();

  return http.get<{
    backup_logs: Array<any>;
    job_status: string;
    message: string;
  }>(`/apis/mysql/bizs/${currentBizId}/fixpoint_rollback/query_latest_backup_log/`, params);
};

export const queryFixpointLog = function (params: {
  cluster_id: number;
  rollback_time: string;
  job_instance_id: number;
}) {
  const { currentBizId } = useGlobalBizs();

  return http
    .get<ListBase<FixpointLogModel[]>>(`/apis/mysql/bizs/${currentBizId}/fixpoint_rollback/query_fixpoint_log/`, params)
    .then((data) => ({
      ...data,
      results: data.results.map((item) => new FixpointLogModel(item)),
    }));
};
