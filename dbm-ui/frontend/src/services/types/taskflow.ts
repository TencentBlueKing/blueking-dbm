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

import type { TicketTypesStrings } from '@common/const';

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
 * 任务列表返回结果
 */
export interface TaskflowResult {
  count: number,
  next: string,
  previous: string,
  results: TaskflowItem[]
}

/**
 * 任务列表项
 */
export interface TaskflowItem {
  root_id: string,
  ticket_type_display: string,
  ticket_type: TicketTypesStrings,
  status: string,
  uid: string,
  created_by: string,
  created_at: string,
  cost_time: number
}

/**
 * 任务流程节点类型
 * ServiceActivity 服务节点（可点击查看）
 * ConvergeGateway 汇聚网关
 * ParallelGateway 并行网关
 * SubProcess 子流程
 * EmptyStartEvent 开始节点
 * EmptyEndEvent 结束节点
 */
export enum FlowTypes {
  ServiceActivity = 'ServiceActivity',
  SubProcess = 'SubProcess',
  ConvergeGateway = 'ConvergeGateway',
  ParallelGateway = 'ParallelGateway',
  EmptyStartEvent = 'EmptyStartEvent',
  EmptyEndEvent = 'EmptyEndEvent',
}
export type FlowType = keyof typeof FlowTypes;

/**
 * 任务节点状态
 */
export type FlowStatus = 'FINISHED' | 'RUNNING' | 'FAILED' | 'READY' | 'CREATED' | 'SKIPPED';

/**
 * 任务流程节点数据
 */
export interface FlowItem {
  id: string,
  name: string | null,
  incoming: string | string[],
  outgoing: string | string[],
  type: FlowType,
  error_ignorable?: boolean,
  optional?: boolean,
  retryable?: boolean,
  skippable?: boolean,
  status?: FlowStatus,
  timeout?: number,
  started_at?: number,
  created_at?: number,
  updated_at?: number,
  component?: {
    code: string
  },
  pipeline?: FlowsData,
}

/**
 * 任务流程节点连接数据
 */
export interface FlowLine {
  id: string,
  source: string,
  target: string,
  is_default: boolean
}

/**
 * 任务流程数据
 */
export interface FlowsData {
  id: string,
  data: any,
  end_event: FlowItem,
  start_event: FlowItem,
  flows: { [key: string]: FlowLine },
  gateways: { [key: string]: FlowItem },
  activities: { [key: string]: FlowItem },
  flow_info: TaskflowItem,
}

/**
 * 节点重试信息
 */
export interface RetryNodeItem {
  started_time: string,
  version: string
}

/**
 * 获取节点日志参数
 */
export interface GetNodeLogParams {
  root_id: string,
  node_id: string,
  version_id: string
}

/**
 * 获取节点日志
 */
export interface NodeLog {
  timestamp: number,
  message: string,
  levelname: string,
}

/**
 * 结果文件列表信息
 */
export interface KeyFileItem {
  name: string,
  size: number,
  size_display: string,
  domain: string,
  created_time: string,
  cluster_alias: string,
  path: string,
  cluster_id: number,
  files: KeyFile[]
}

/**
 * 结果文件信息
 */
export interface KeyFile {
  size: string,
  name: string,
  md5: string,
  full_path: string,
  created_time: string,
}
