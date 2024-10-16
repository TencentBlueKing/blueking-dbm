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

import FlowMode from '@services/model/ticket/flow';

import http from '../http';

const path = '/apis/tickets';

/**
 * 获取单据流程
 */
export function getTicketFlows(params: { id: number }) {
  return http
    .get<FlowMode<unknown>[]>(`${path}/${params.id}/flows/`)
    .then((data) => data.map((item) => new FlowMode(item)));
}

// 单据流程重试
export function retryFlow(params: { id: number; flow_id: number }) {
  return http.post(`${path}/${params.id}/retry_flow/`, { flow_id: params.flow_id });
}

// 单据流程终止
export function revokeFlow(params: { id: number; flow_id: number }) {
  return http.post(`${path}/${params.id}/revoke_flow/`, { flow_id: params.flow_id });
}

export function processTodo(params: { id: number; todo_id: number; action: string; params: Record<string, any> }) {
  const realParams = { ...params } as { id?: number };
  delete realParams.id;

  return http.post(`${path}/${params.id}/process_todo/`, realParams);
}

// 获取单据数量
export function getTicketCount() {
  return http.get<{
    MY_APPROVE: number;
    APPROVE: number;
    TODO: number;
    RUNNING: number;
    RESOURCE_REPLENISH: number;
    FAILED: number;
    DONE: number;
    SELF_MANAGE: number;
  }>(`${path}/get_tickets_count/`);
}

// 批量处理单据的待办
export function batchProcessTicket(params: {
  action: 'APPROVE' | 'TERMINATE';
  ticket_ids: number[];
  params?: Record<string, any>;
}) {
  return http.post(`${path}/batch_process_ticket/`, params);
}

// /apis/tickets/batch_process_todo/
export function batchProcessTodo(params: {
  action: 'APPROVE' | 'TERMINATE';
  operations: {
    todo_id: number;
    params?: Record<string, any>;
  }[];
}) {
  return http.post(`${path}/batch_process_todo/`, params);
}
