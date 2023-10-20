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

import http from './http';
import type {
  FlowsData,
  GetNodeLogParams,
  GetTaskflowParams,
  KeyFileItem,
  NodeLog,
  RetryNodeItem,
  TaskflowResult,
} from './types/taskflow';

/**
 * 查询任务列表
 */
export const getTaskflow = (params: GetTaskflowParams) => http.get<TaskflowResult>('/apis/taskflow/', params);

/**
 * 查询任务详情流程
 */
export const getTaskflowDetails = (params: { rootId: string }) => http.get<FlowsData>(`/apis/taskflow/${params.rootId}/`);

/**
 * 重试任务详情节点
 */
export const retryTaskflowNode = (params: {
  root_id: string,
  node_id: string
}) => http.post<{ node_id: string}>(`/apis/taskflow/${params.root_id}/retry_node/`, params);

/**
 * 跳过任务详情节点
 */
export const skipTaskflowNode = (params: {
  root_id: string,
  node_id: string
}) => http.post<{ node_id: string}>(`/apis/taskflow/${params.root_id}/skip_node/`, params);

/**
 * 终止任务流程
 */
export const revokePipeline = (params: { rootId: string }) => http.post(`/apis/taskflow/${params.rootId}/revoke_pipeline/`);

/**
 * 节点重试版本列表
 */
export const getRetryNodeHistories = (params: {
  root_id: string,
  node_id: string
}) => http.get<RetryNodeItem[]>(`/apis/taskflow/${params.root_id}/node_histories/`, params);

/**
 * 节点重试版本列表
 */
export const getNodeLog = (params: GetNodeLogParams) => http.get<NodeLog[]>(`/apis/taskflow/${params.root_id}/node_log/`, params);

/**
 * 获取结果文件列表
 */
export const getKeyFiles = (params: { rootId: string }) => http.get<KeyFileItem[]>(`/apis/taskflow/redis/${params.rootId}/key_files/`);

/**
 * 获取结果文件地址
 */
export const getRedisFileUrls = (params: {
  root_id: string,
  paths: string[]
}) => http.post<Record<string, string>>('/apis/taskflow/redis/download_dirs/', params);
