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
import http from '@services/http';
import RedisDSTHistoryJobModel from '@services/model/redis/redis-dst-history-job';
import RedisDSTJobTaskModel from '@services/model/redis/redis-dst-job-task';

import { useGlobalBizs } from '@stores';

const { currentBizId } = useGlobalBizs();

const path = `/apis/redis/bizs/${currentBizId}/dts`;

/**
 * 获取DTS历史任务以及其对应task cnt
 */
export function getRedisDTSHistoryJobs(params: {
  start_time?: string,
  end_time?: string,
  cluster_name?: string,
  page?: number,
  page_size?: number,
}) {
  return http.post<{ total_cnt: number, jobs: RedisDSTHistoryJobModel[]}>(`${path}/history_jobs/`, params);
}

/**
 * dts job批量断开同步
 */
export function setJobDisconnectSync(params: {
  bill_id: number,
  src_cluster: string,
  dst_cluster: string,
}) {
  return http.post<unknown>(`${path}/job_disconnect_sync/`, params);
}

/**
 * dts job 批量失败重试
 */
export function setJobTaskFailedRetry(params: {
  task_ids: number[]
}) {
  return http.post<number[]>(`${path}/job_task_failed_retry/`, params);
}

/**
 * 获取迁移任务task列表,失败的排在前面
 */
export function getRedisDTSJobTasks(params: {
  bill_id: number,
  src_cluster: string,
  dst_cluster: string,
}) {
  return http.post<RedisDSTJobTaskModel[]>(`${path}/job_tasks/`, params)
    .then(arr => arr.map(item => new RedisDSTJobTaskModel(item)));
}

/**
 * dts 外部redis连接行测试
 */
export function testRedisConnection(params: {
  data_copy_type: string,
  infos: {
    src_cluster: string,
    src_cluster_password: string,
    dst_cluster: string,
    dst_cluster_password: string,
  }[]
}) {
  return http.post<boolean>(`${path}/test_redis_connection/`, params);
}
