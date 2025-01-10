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
import InfoBox from 'bkui-vue/lib/info-box';

import TicketModel from '@services/model/ticket/ticket';
import TicketFlowDescribeModel from '@services/model/ticket-flow-describe/TicketFlowDescribe';
import type { HostNode, ListBase } from '@services/types';
import type { FlowItem, FlowItemTodo } from '@services/types/ticket';

import { getRouter } from '@router/index';

import { messageError } from '@utils';

import { locale, t } from '@locales/index';

import http, { type IRequestPayload } from '../http';

const path = '/apis/tickets';

/**
 * 单据列表
 */
export function getTickets(params: {
  id?: number;
  bk_biz_id?: number;
  ticket_type?: string;
  status?: string;
  limit?: number;
  offset?: number;
  create_at__lte?: string;
  create_at__gte?: string;
  remark?: string;
  creator?: string;
  cluster?: string;
  todo?: string;
  self_manage?: number;
  ordering?: string;
  is_assist?: boolean;
}) {
  return http.get<ListBase<TicketModel[]>>(`${path}/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new TicketModel(item)),
  }));
}

/**
 * 创建单据
 */
export function createTicket(formData: Record<string, any>) {
  return http
    .post<{ id: number }>(`${path}/`, formData, { catchError: true })
    .then((res) => res)
    .catch((e) => {
      const { code, data } = e;
      const duplicateCode = 8704005;
      if (code === duplicateCode) {
        const id = data.duplicate_ticket_id;
        const router = getRouter();

        console.log('router = ', router);

        const route = router.resolve({
          name: 'bizTicketManage',
          params: {
            ticketId: id,
          },
        });
        return new Promise<{ id: number }>((resolve, reject) => {
          InfoBox({
            title: t('是否继续提交单据'),
            content: () => {
              if (locale.value === 'en') {
                return (
                  <span>
                    You have already submitted a
                    <a
                      href={route.href}
                      target='_blank'>
                      {' '}
                      ticket[{id}]{' '}
                    </a>
                    with the same target cluster, continue?
                  </span>
                );
              }

              return (
                <span>
                  你已提交过包含相同目标集群的
                  <a
                    href={route.href}
                    target='_blank'>
                    单据[{id}]
                  </a>
                  ，是否继续？
                </span>
              );
            },
            confirmText: t('继续提单'),
            cancelText: t('取消提单'),
            onConfirm: async () => {
              try {
                const res = await createTicket({
                  ...formData,
                  ignore_duplication: true,
                });
                return resolve(res);
              } catch (e: any) {
                messageError(e?.message);
                return reject(e);
              }
            },
            onCancel: () => {
              reject(e);
            },
          });
        });
      }

      messageError(e.message);

      return Promise.reject(e);
    });
}

/**
 * 获取单据类型列表
 */
export function getTicketTypes(params?: { is_apply: 0 | 1 }) {
  return http.get<
    {
      key: string;
      value: string;
    }[]
  >(`${path}/flow_types/`, params ?? {});
}

/**
 * 查询集群变更单据事件
 */
export function getClusterOperateRecords(params: Record<string, unknown> & { cluster_id: number }) {
  return http.get<
    ListBase<
      {
        create_at: string;
        ticket_id: number;
        op_type: string;
        op_status: 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'REVOKED';
      }[]
    >
  >(`${path}/get_cluster_operate_records/`, params);
}

/**
 * 查询集群实例变更单据事件
 */
export function getInstanceOperateRecords(params: Record<string, unknown> & { instance_id: number }) {
  return http.get<
    ListBase<
      {
        create_at: string;
        ticket_id: number;
        op_type: string;
        op_status: 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'REVOKED';
      }[]
    >
  >(`${path}/get_instance_operate_records/`, params);
}

/**
 * 待办单据数
 */
export function getTicketsCount(params: { count_type: 'MY_TODO' | 'MY_APPROVE' }) {
  return http.get<number>(`${path}/get_tickets_count/`, params);
}

/**
 * 待办单据列表
 */
export function getTodoTickets(
  params: {
    bk_biz_id?: number;
    ticket_type?: string;
    status?: string;
    limit?: number;
    offset?: number;
    create_at__lte?: string;
    create_at__gte?: string;
    remark?: string;
    creator?: string;
    cluster?: string;
    todo_status?: string;
    status__in?: string;
  } = {},
) {
  return http.get<ListBase<TicketModel<unknown>[]>>(`${path}/get_todo_tickets/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new TicketModel(item)),
  }));
}

/**
 * 单据详情
 */
export function getTicketDetails<T extends TicketModel = TicketModel<unknown>>(
  params: {
    id: number;
    is_reviewed?: number;
  },
  payload = {} as IRequestPayload,
) {
  return http.get<T>(`${path}/${params.id}/`, params, payload).then((data) => new TicketModel(data) as T);
}

/**
 * 获取单据流程
 */
export function getTicketFlows(params: { id: number }) {
  return http.get<FlowItem[]>(`${path}/${params.id}/flows/`);
}

/**
 * 节点列表
 */
export function getTicketHostNodes(params: { bk_biz_id: number; id: number; role: string; keyword?: string }) {
  return http.get<HostNode[]>(`${path}/${params.id}/get_nodes/`, params);
}

/**
 * 待办处理
 */
export function processTicketTodo(params: {
  action: string;
  todo_id: number;
  ticket_id: number;
  params: Record<string, any>;
}) {
  return http.post<FlowItemTodo>(`${path}/${params.ticket_id}/process_todo/`, params);
}

/**
 * 单据流程重试
 */
export function retryTicketFlow(params: { ticketId: number; flow_id: number }) {
  return http.post(`${path}/${params.ticketId}/retry_flow/`, params);
}

/**
 * 查询可编辑单据流程描述
 */
export function queryTicketFlowDescribe(params: {
  db_type: string;
  ticket_types?: string;
  limit?: number;
  offset?: number;
  bk_biz_id?: number;
}) {
  return http.get<TicketFlowDescribeModel[]>(`${path}/query_ticket_flow_describe/`, params).then((data) => ({
    count: data.length || 0,
    results: data.map((item) => new TicketFlowDescribeModel(item)) || [],
  }));
}

/**
 * 创建单据流程规则
 */
export function createTicketFlowConfig(params: {
  ticket_types: string[];
  configs: Record<string, boolean>;
  bk_biz_id: number;
  cluster_ids?: number[];
}) {
  return http.post<{
    ticket_types: string[];
  }>(`${path}/create_ticket_flow_config/`, params);
}

/**
 * 修改可编辑的单据流程规则
 */
export function updateTicketFlowConfig(params: {
  ticket_types: string[];
  configs: Record<string, boolean>;
  bk_biz_id: number;
  cluster_ids?: number[];
  config_ids?: number[];
}) {
  return http.post<{
    ticket_types: string[];
  }>(`${path}/update_ticket_flow_config/`, params);
}

export function getTicketStatus(params: { ticket_ids: string }) {
  return http.get<Record<string, string>>(`${path}/list_ticket_status/`, params, {
    cache: 1000,
  });
}

/**
 * 删除单据流程规则
 */
export function deleteTicketFlowConfig(params: { config_ids: number[] }) {
  return http.delete<{
    ticket_types: string[];
  }>(`${path}/delete_ticket_flow_config/`, params);
}

/**
 * 查询服务器资源的城市信息
 */
export const getInfrasCities = () =>
  http.get<
    {
      city_code: string;
      city_name: string;
      inventory: number;
      inventory_tag: string;
    }[]
  >('/apis/infras/cities/');

/**
 * 服务器规格列表
 */
export const getInfrasHostSpecs = () =>
  http.get<
    {
      cpu: string;
      mem: string;
      spec: string;
      type: string;
    }[]
  >('/apis/infras/cities/host_specs/');

/**
 * redis 容量列表
 */
export const getCapSpecs = (params: {
  nodes: {
    master: Array<{
      ip: string;
      bk_cloud_id: number;
      bk_host_id: number;
      bk_cpu?: number;
      bk_mem?: number;
      bk_disk?: number;
      bk_biz_id: number;
    }>;
    slave: Array<{
      ip: string;
      bk_cloud_id: number;
      bk_host_id: number;
      bk_cpu?: number;
      bk_mem?: number;
      bk_disk?: number;
      bk_biz_id: number;
    }>;
  };
  ip_source: string;
  cluster_type: string;
  cityCode: string;
}) =>
  http.post<
    {
      group_num: number;
      maxmemory: number;
      shard_num: number;
      spec: string;
      total_memory: number;
      cap_key: string;
      selected: boolean;
      max_disk: number;
      total_disk: string;
    }[]
  >('/apis/infras/cities/cap_specs/', params);

/**
 * 创建业务英文缩写
 */
export const createAppAbbr = (params: { db_app_abbr: string; id: number }) =>
  http.post<{
    db_app_abbr: string;
  }>(`/apis/cmdb/${params.id}/set_db_app_abbr/`, params);

/**
 * 创建模块
 */
// export const createModules = (params: { db_module_name: string; cluster_type: string; id: number }) =>
//   http.post<{
//     db_module_id: number;
//     db_module_name: string;
//     cluster_type: string;
//     bk_biz_id: number;
//     bk_set_id: number;
//     bk_modules: { bk_module_name: string; bk_module_id: string }[];
//     name: string;
//   }>(`/apis/cmdb/${params.id}/create_module/`, params);

/**
 * 保存模块配置
 */
export const saveModulesDeployInfo = (params: {
  bk_biz_id: number;
  conf_items: {
    conf_name: string;
    conf_value: string;
    op_type: string;
  }[];
  version: string;
  meta_cluster_type: string;
  level_name: string;
  level_value: number;
  conf_type: string;
}) =>
  http.post<{
    bk_biz_id: number;
    conf_items: {
      conf_name: string;
      conf_value: string;
      op_type: string;
    }[];
    version: string;
    meta_cluster_type: string;
    level_name: string;
    level_value: number;
    conf_type: string;
  }>('/apis/configs/save_module_deploy_info/', params);

/**
 * 查询访问源列表
 */
export const getHostInAuthorize = (params: {
  bk_biz_id: string;
  ticket_id: number;
  limit?: number;
  offset?: number;
  keyword?: string;
}) =>
  http
    .get<{
      hosts: HostNode[];
      ip_whitelist: { ip: string }[];
    }>(`/apis/mysql/bizs/${params.bk_biz_id}/permission/authorize/get_host_in_authorize/`, params)
    .then((res) => {
      const list = [...res.hosts];

      for (const item of res.ip_whitelist) {
        list.push({
          bk_host_innerip: item.ip,
        } as HostNode);
      }

      return list;
    });

/**
 * 单据流程终止
 */
export function revokeTicketFlow(params: { ticketId: number; flow_id: number }) {
  return http.post(`${path}/${params.ticketId}/revoke_flow/`, params);
}

/**
 * 批量待办处理
 */
export function ticketBatchProcessTodo(params: {
  action: 'APPROVE' | 'TERMINATE';
  operations: {
    todo_id: number;
    params: Record<string, never>; // 暂时为空对象
  }[];
}) {
  return http.post(`${path}/batch_process_todo/`, params);
}
