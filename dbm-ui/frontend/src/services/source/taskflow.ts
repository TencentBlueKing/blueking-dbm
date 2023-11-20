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

import http from '../http';
import type { ListBase } from '../types';
import type {
  FlowsData,
  KeyFileItem,
  NodeLog,
  RetryNodeItem,
  TaskflowItem,
} from '../types/taskflow';

const path = '/apis/taskflow';

/**
 * 查询任务列表参数
 */
export interface GetTaskflowParams {
  bk_biz_id: number,
  limit: number,
  offset: number
  root_id?: string,
  uid?: number,
  status?: string,
  status__in?: string,
  ticket_type?: string,
  ticket_type__in?: string,
  created_at__gte?: string,
  created_at__lte?: string,
}

/**
 * 查询任务列表
 */
export const getTaskflow = function (params: GetTaskflowParams) {
  return http.get<ListBase<TaskflowItem[]>>(`${path}/`, params);
};

/**
 * 指定目录下载（返回下载链接）
 */
export const getRedisFileUrls = function (params: {
  root_id: string,
  paths: string[]
}) {
  return http.post<Record<string, string>>(`${path}/redis/download_dirs/`, params);
};

/**
 * 结果文件列表
 */
export const getKeyFiles = function (params: { rootId: string }) {
  return http.get<KeyFileItem[]>(`${path}/redis/${params.rootId}/key_files/`);
};

/**
 * 任务详情
 */
export const getTaskflowDetails = function (params: { rootId: string }) {
  return http.get<FlowsData>(`${path}/${params.rootId}/`);
};

/**
 * 节点版本列表
 */
export const getRetryNodeHistories = function (params: {
  root_id: string,
  node_id: string
}) {
  return http.get<RetryNodeItem[]>(`${path}/${params.root_id}/node_histories/`, params);
};

/**
 * 节点日志
 */
export const getNodeLog = function (params: {
  root_id: string,
  node_id: string,
  version_id: string
}) {
  return http.get<NodeLog[]>(`${path}/${params.root_id}/node_log/`, params);
};

/**
 * 重试节点
 */
export const retryTaskflowNode = function (params: {
  root_id: string,
  node_id: string
}) {
  return http.post<{ node_id: string}>(`${path}/${params.root_id}/retry_node/`, params);
};

/**
 * 撤销流程
 */
export const revokePipeline = function (params: { rootId: string }) {
  return http.post(`${path}/${params.rootId}/revoke_pipeline/`);
};

/**
 * 跳过节点
 */
export const skipTaskflowNode = function (params: {
  root_id: string,
  node_id: string
}) {
  return http.post<{ node_id: string}>(`${path}/${params.root_id}/skip_node/`, params);
};
