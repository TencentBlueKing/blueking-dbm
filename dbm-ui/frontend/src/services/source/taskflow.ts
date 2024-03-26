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

import TaskFlowModel from '@services/model/taskflow/taskflow';

import http, { type IRequestPayload } from '../http';
import type { ListBase } from '../types';

const path = '/apis/taskflow';

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

/**
 * 查询任务列表
 */
export function getTaskflow(params: {
  bk_biz_id: number;
  limit: number;
  offset: number;
  root_id?: string;
  uid?: number;
  status?: string;
  status__in?: string;
  ticket_type?: string;
  ticket_type__in?: string;
  created_at__gte?: string;
  created_at__lte?: string;
}) {
  return http.get<ListBase<TaskFlowModel[]>>(`${path}/`, params).then((res) => ({
    ...res,
    results: res.results.map((item) => new TaskFlowModel(item)),
  }));
}

/**
 * 指定目录下载（返回下载链接）
 */
export function getRedisFileUrls(params: { root_id: string; paths: string[] }) {
  return http.post<Record<string, string>>(`${path}/redis/download_dirs/`, params);
}

/**
 * 结果文件列表
 */
export function getKeyFiles(params: { rootId: string }) {
  return http.get<
    {
      name: string;
      size: number;
      size_display: string;
      domain: string;
      created_time: string;
      cluster_alias: string;
      path: string;
      cluster_id: number;
      files: {
        size: string;
        name: string;
        md5: string;
        full_path: string;
        created_time: string;
      }[];
    }[]
  >(`${path}/redis/${params.rootId}/key_files/`);
}

/**
 * 任务流程数据
 */
interface FlowsDetail {
  activities: {
    [key: string]: {
      component?: {
        code: string;
      };
      created_at?: number;
      error_ignorable?: boolean;
      hosts: string[];
      id: string;
      incoming: string[];
      name?: string;
      optional: boolean;
      outgoing: string;
      pipeline?: FlowsDetail;
      retryable: boolean;
      skippable: boolean;
      started_at: number;
      status: 'FINISHED' | 'RUNNING' | 'FAILED' | 'READY' | 'CREATED' | 'SKIPPED';
      timeout?: number;
      type: keyof typeof FlowTypes;
      updated_at: number;
    };
  };
  data: {
    outputs: any[];
    pre_render_keys: any[];
  };
  end_event: {
    id: string;
    incoming: string[];
    name?: string;
    outgoing: string;
    type: keyof typeof FlowTypes;
    error_ignorable?: boolean;
  };
  flow_info: {
    bk_biz_id: number;
    bk_host_ids: number[];
    cost_time: number;
    created_at: string;
    created_by: string;
    root_id: string;
    status: string;
    ticket_type: string;
    ticket_type_display: string;
    uid: string;
    updated_at: string;
  };
  flows: {
    [key: string]: {
      id: string;
      is_default: boolean;
      source: string;
      target: string;
    };
  };
  gateways: { [key: string]: FlowsDetail['end_event'] };
  id: string;
  start_event: FlowsDetail['end_event'];
}

/**
 * 任务详情
 */
export function getTaskflowDetails(params: { rootId: string }, payload = {} as IRequestPayload) {
  return http.get<FlowsDetail>(`${path}/${params.rootId}/`, {}, payload);
}

/**
 * 节点版本列表
 */
export function getRetryNodeHistories(params: { root_id: string; node_id: string }) {
  return http.get<
    {
      started_time: string;
      version: string;
      cost_time: number;
    }[]
  >(`${path}/${params.root_id}/node_histories/`, params);
}

/**
 * 节点日志
 */
export function getNodeLog(params: { root_id: string; node_id: string; version_id: string }) {
  return http.get<
    {
      timestamp: number;
      message: string;
      levelname: string;
    }[]
  >(`${path}/${params.root_id}/node_log/`, params);
}

/**
 * 重试节点
 */
export function retryTaskflowNode(params: { root_id: string; node_id: string }) {
  return http.post<{ node_id: string }>(`${path}/${params.root_id}/retry_node/`, params);
}

/**
 * 撤销流程
 */
export function revokePipeline(params: { rootId: string }) {
  return http.post(`${path}/${params.rootId}/revoke_pipeline/`);
}

/**
 * 跳过节点
 */
export function skipTaskflowNode(params: { root_id: string; node_id: string }) {
  return http.post<{ node_id: string }>(`${path}/${params.root_id}/skip_node/`, params);
}

/**
 * 强制失败节点
 */
export function forceFailflowNode(params: { root_id: string; node_id: string }) {
  return http.post<{ node_id: string }>(`${path}/${params.root_id}/force_fail_node/`, params);
}
