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

import TicketModel from '@services/model/ticket/ticket';

import { useInfo } from '@hooks';

import { getRouter } from '@router/index';

import { messageError } from '@utils';

import { locale, t } from '@locales/index';

import http from '../http';
import type {
  HostNode,
  ListBase,
} from '../types/common';
import type {
  ClusterOperateRecord,
  FlowItem,
  FlowItemTodo,
  TicketType,
} from '../types/ticket';

const path = '/apis/tickets';

/**
 * 单据列表
 */
export const getTickets = function (params: {
  bk_biz_id?: number,
  ticket_type?: string,
  status?: string,
  limit?: number,
  offset?: number,
} = {}) {
  return http.get<ListBase<TicketModel[]>>(`${path}/`, params).then(data => ({
    ...data,
    results: data.results.map(item => new TicketModel(item)),
  }));
};

/**
 * 单据列表项
 */
export interface TicketItem {
  db_app_abbr: string,
  bk_biz_id: number,
  bk_biz_name: string,
  cost_time: number,
  create_at: string,
  creator: string,
  details: any,
  id: number,
  remark: string,
  status: string,
  status_display: string,
  ticket_type: string,
  ticket_type_display: string,
  update_at: string,
  updater: string,
  is_reviewed: boolean,
  related_object: {
    title: string,
    objects: string[]
  }
}

/**
 * 创建单据
 */
export const createTicket = function (formData: Record<string, any>) {
  return http.post<TicketItem>(`${path}/`, formData, { globalError: false })
    .then(res => res)
    .catch((e) => {
      const {
        code,
        data,
      } = e;
      const duplicateCode = 8704005;
      if (code === duplicateCode) {
        const id = data.duplicate_ticket_id;
        const router = getRouter();
        const route = router.resolve({
          name: 'SelfServiceMyTickets',
          query: {
            filterId: id,
          },
        });
        return new Promise((resolve: (value: TicketItem) => void, reject) => {
          useInfo({
            title: t('是否继续提交单据'),
            content: () => {
              if (locale.value === 'en') {
                return (
                <span>
                  You have already submitted a
                  <a href={route.href} target="_blank"> ticket[{id}] </a>
                  with the same target cluster, continue?
                </span>
                );
              }

              return (
              <span>
                你已提交过包含相同目标集群的
                <a href={route.href} target="_blank">单据[{id}]</a>
                ，是否继续？
              </span>
              );
            },
            confirmTxt: t('继续提单'),
            cancelTxt: t('取消提单'),
            onConfirm: async () => {
              try {
                const res = await createTicket({
                  ...formData,
                  ignore_duplication: true,
                });
                resolve(res);
                return true;
              } catch (e: any) {
                messageError(e?.message);
                reject(e);
                return false;
              }
            },
            onCancel: () => {
              reject(e);
            },
          });
        });
      }

      messageError(e?.message);
      return Promise.reject(e);
    });
};

/**
 * 获取单据类型列表
 */
export const getTicketTypes = function (params?: { is_apply: 0 | 1 }) {
  return http.get<TicketType[]>(`${path}/flow_types/`, params ?? {});
};

/**
  * 查询集群变更单据事件
  */
export const getClusterOperateRecords = function (params: Record<string, unknown> & { cluster_id: number }) {
  return http.get<ListBase<ClusterOperateRecord[]>>(`${path}/get_cluster_operate_records/`, params);
};

/**
  * 查询集群实例变更单据事件
  */
export const getInstanceOperateRecords = function (params: Record<string, unknown> & { instance_id: number }) {
  return http.get<ListBase<ClusterOperateRecord[]>>(`${path}/get_instance_operate_records/`, params);
};

/**
  * 待办单据数
  */
export const getTicketsCount = function (params: { count_type: 'MY_TODO' | 'MY_APPROVE' }) {
  return http.get<number>(`${path}/get_tickets_count/`, params);
};

/**
 * 待办单据列表
 */
export const getTodoTickets = function (params: {
  bk_biz_id?: number,
  ticket_type?: string,
  status?: string,
  limit?: number,
  offset?: number,
} = {}) {
  return http.get<ListBase<TicketModel[]>>(`${path}/get_todo_tickets/`, params).then(data => ({
    ...data,
    results: data.results.map(item => new TicketModel(item)),
  }));
};

/**
 * 单据详情
 */
export const getTicketDetails = function (params: {
  id: number,
  is_reviewed?: number
}) {
  return http.get<TicketModel>(`${path}/${params.id}/`, params).then(data => new TicketModel(data));
};

/**
 * 获取单据流程
 */
export const getTicketFlows = function (params: { id: number }) {
  return http.get<FlowItem[]>(`${path}/${params.id}/flows/`);
};

/**
 * 节点列表
 */
export const getTicketHostNodes = function (params: {
  bk_biz_id: number,
  id: number,
  role: string,
  keyword?: string
}) {
  return http.get<HostNode[]>(`${path}/${params.id}/get_nodes/`, params);
};

/**
 * 待办处理
 */
export const processTicketTodo = function (params: {
  action: string,
  todo_id: number,
  ticket_id: number,
  params: Record<string, any>
}) {
  return http.post<FlowItemTodo>(`${path}/${params.ticket_id}/process_todo/`, params);
};

/**
  * 单据流程重试
  */
export const retryTicketFlow = function (params: {
  ticketId: number,
  flow_id: number
}) {
  return http.post(`${path}/${params.ticketId}/retry_flow/`, params);
};
