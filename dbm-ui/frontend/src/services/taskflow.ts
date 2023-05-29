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
export const getTaskflow = (params: GetTaskflowParams): Promise<TaskflowResult> => http.get('/apis/taskflow/', params);

/**
 * 查询任务详情流程
 */
export const getTaskflowDetails = (rootId: string): Promise<FlowsData> => http.get(`/apis/taskflow/${rootId}/`);

/**
 * 重试任务详情节点
 */
export const retryTaskflowNode = ({ root_id: rootId, node_id }: { root_id: string, node_id: string }): Promise<{ node_id: string}> => http.post(`/apis/taskflow/${rootId}/retry_node/`, { node_id });

/**
 * 跳过任务详情节点
 */
export const skipTaskflowNode = ({ root_id: rootId, node_id }: { root_id: string, node_id: string }): Promise<{ node_id: string}> => http.post(`/apis/taskflow/${rootId}/skip_node/`, { node_id });

/**
 * 终止任务流程
 */
export const revokePipeline = (rootId: string) => http.post(`/apis/taskflow/${rootId}/revoke_pipeline/`);

/**
 * 节点重试版本列表
 */
export const getRetryNodeHistories = ({ root_id: rootId, node_id }: { root_id: string, node_id: string }): Promise<RetryNodeItem[]> => http.get(`/apis/taskflow/${rootId}/node_histories/`, { node_id });

/**
 * 节点重试版本列表
 */
export const getNodeLog = (params: GetNodeLogParams): Promise<NodeLog[]> => http.get(`/apis/taskflow/${params.root_id}/node_log/`, params);

/**
 * 获取结果文件列表
 */
export const getKeyFiles = (rootId: string): Promise<KeyFileItem[]> => http.get(`/apis/taskflow/redis/${rootId}/key_files/`);

/**
 * 获取结果文件地址
 */
export const getRedisFileUrls = (rootId: string, paths: string[]): Promise<Record<string, string>> => http.post('/apis/taskflow/redis/download_dirs/', { paths, root_id: rootId });
