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
import TicketClusterDisableTodoModel from '@services/model/ticket-cluster-disable-todo/TicketClusterDisableTodo';
import TicketFlowDescribeModel from '@services/model/ticket-flow-describe/TicketFlowDescribe';
import type { HostNode, ListBase } from '@services/types';
import type { FlowItem, FlowItemTodo } from '@services/types/ticket';

import { getRouter } from '@router';

import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

import { messageError } from '@utils';

import { locale, t } from '@locales/index';

import http, { type IRequestPayload } from '../http';
import type { DetailClusters } from '../model/ticket/details/common';

const path = '/apis/tickets';

/**
 * 单据列表
 */
export function getTickets(params: {
  bk_biz_id?: number;
  cluster?: string;
  create_at__gte?: string;
  create_at__lte?: string;
  creator?: string;
  id?: number;
  ids?: string;
  is_assist?: boolean;
  limit?: number;
  offset?: number;
  ordering?: string;
  remark?: string;
  replenish_db_type?: string;
  self_manage?: number;
  status?: string;
  ticket_type?: string;
  todo?: string;
}) {
  return http.get<ListBase<TicketModel[]>>(`${path}/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new TicketModel(item)),
  }));
}

/**
 * 创建单据
 */
export function createTicketNew<T>(params: {
  bk_biz_id: number;
  details: T;
  ignore_duplication?: boolean;
  remark: string;
  ticket_type: TicketTypes;
}) {
  return http.post<{ id: number }>(`${path}/`, params, {
    catchError: true,
    timeout: 300000,
  });
}

/**
 * 批量创建单据
 */
export function createTicketBatch<T>(params: {
  tickets: {
    bk_biz_id: number;
    details: T;
    ignore_duplication?: boolean;
    remark: string;
    ticket_type: TicketTypes;
  }[];
}) {
  return http.post<{ bk_biz_id: number; clusters: DetailClusters; id: number }[]>(
    `${path}/batch_create_ticket/`,
    params,
    {
      catchError: true,
      timeout: 300000,
    },
  );
}

/**
 * 创建单据、过后摒弃
 */
export function createTicket(formData: Record<string, any>) {
  return http
    .post<{ bk_biz_id: number; id: number }>(`${path}/`, formData, {
      catchError: true,
      timeout: 300000,
    })
    .then((res) => res)
    .catch((e) => {
      const { code, data } = e;
      const duplicateCode = 8704005;
      if (code === duplicateCode) {
        const id = data.duplicate_ticket_id;
        const router = getRouter();

        const route = router.resolve({
          name: 'SelfServiceMyTickets',
          params: {
            ticketId: id,
          },
        });
        return new Promise<{ bk_biz_id: number; id: number }>((resolve, reject) => {
          InfoBox({
            cancelText: t('取消提单'),
            confirmText: t('继续提单'),
            content: () => {
              if (locale.value === 'en') {
                return (
                  <span>
                    The system has detected that a similar ticket has already been submitted
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
                  系统检测到已提交过包含相同集群的同类
                  <a
                    href={route.href}
                    target='_blank'>
                    单据[{id}]
                  </a>
                  ，是否继续？
                </span>
              );
            },
            onCancel: () => {
              reject(e);
            },
            onConfirm: async () => {
              try {
                const res = await createTicket({
                  ...formData,
                  ignore_duplication: true,
                });
                window.changeConfirm = false;
                return resolve(res);
              } catch (e: any) {
                messageError(e?.message);
                return reject(e);
              }
            },
            title: t('是否继续提交单据'),
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

export function getTicketGroupTypes() {
  return http.get<
    {
      children: {
        label: string;
        value: string;
      }[];
      label: string;
      value: string;
    }[]
  >(
    `${path}/ticket_group_types/`,
    {},
    {
      cache: true,
    },
  );
}

/**
 * 查询集群变更单据事件
 */
export function getClusterOperateRecords(params: { cluster_id: number } & Record<string, unknown>) {
  return http.get<
    ListBase<
      {
        create_at: string;
        creator: string;
        op_status: 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'REVOKED';
        op_type: string;
        remark: string;
        ticket_id: number;
      }[]
    >
  >(`${path}/get_cluster_operate_records/`, params);
}

/**
 * 查询集群实例变更单据事件
 */
export function getInstanceOperateRecords(params: { instance_id: number } & Record<string, unknown>) {
  return http.get<
    ListBase<
      {
        create_at: string;
        op_status: 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'REVOKED';
        op_type: string;
        ticket_id: number;
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
    cluster?: string;
    create_at__gte?: string;
    create_at__lte?: string;
    creator?: string;
    limit?: number;
    offset?: number;
    remark?: string;
    status?: string;
    status__in?: string;
    ticket_type?: string;
    todo_status?: string;
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
export function getTicketHostNodes(params: { bk_biz_id: number; id: number; keyword?: string; role: string }) {
  return http.get<HostNode[]>(`${path}/${params.id}/get_nodes/`, params);
}

/**
 * 待办处理
 */
export function processTicketTodo(params: {
  action: string;
  params: Record<string, any>;
  ticket_id: number;
  todo_id: number;
}) {
  return http.post<FlowItemTodo>(`${path}/${params.ticket_id}/process_todo/`, params);
}

/**
 * 单据流程重试
 */
export function retryTicketFlow(params: { flow_id: number; ticketId: number }) {
  return http.post(`${path}/${params.ticketId}/retry_flow/`, params);
}

/**
 * 查询可编辑单据流程描述
 */
export function queryTicketFlowDescribe(params: {
  bk_biz_id?: number;
  db_type: string;
  limit?: number;
  offset?: number;
  ticket_types?: string;
}) {
  return http.get<TicketFlowDescribeModel[]>(`${path}/query_ticket_flow_describe/`, params).then((data) => ({
    count: data.length || 0,
    results: data.map((item) => new TicketFlowDescribeModel(item)) || [],
  }));
}

/**
 * 修改可编辑的单据流程规则
 */
export function updateTicketFlowConfig(params: {
  bk_biz_id: number;
  cluster_ids?: number[];
  config_ids?: number[];
  configs: Record<string, boolean>;
  remark?: string;
  ticket_types: string[];
}) {
  return http.post<{
    ticket_types: string[];
  }>(`${path}/update_ticket_flow_config/`, params);
}

/**
 * 子策略按集群标签圈选：标签条件元素
 * - 单值：1 条，tag_value 为具体值
 * - 多值 in：N 条同 tag_key，每条一个 tag_value
 * - 任意值 exists：1 条，tag_value 固定为 '任意值'
 * 每条子策略仅一个 tag_key（不支持多键 AND）
 */
export interface ClusterTagItem {
  id: number;
  /** 标签键是否已失效（后端返回，true 表示该标签键/值已从业务移除） */
  is_invalid?: boolean;
  tag_key: string;
  tag_value: string;
}

/**
 * 按集群子策略的集群元素（cluster_ids 由 number[] 调整为对象数组）
 */
export interface ClusterIdItem {
  id: number;
  immute_domain: string;
}

/**
 * 保存单据流程规则（新建或更新，后端统一接口）
 *
 * 子策略生效范围：
 * - 按集群：cluster_ids 传对象数组，cluster_tags 传 []
 * - 按标签：cluster_ids 传 []，cluster_tags 传标签条件数组
 * config_ids 非空代表编辑。
 */
export function saveTicketFlowConfig(params: {
  bk_biz_id: number;
  cluster_ids?: ClusterIdItem[];
  cluster_tags?: ClusterTagItem[];
  config_ids?: number[];
  configs: {
    need_itsm: boolean;
  };
  remark?: string;
  ticket_types: string[];
}) {
  return http.post<{
    ticket_types: string[];
  }>(`${path}/save_ticket_flow_config/`, params);
}

/**
 * 校验按集群子策略的集群是否已在其他按集群子策略中（同一单据类型下不可重复）
 *
 * 响应中 validate 为 true 表示该集群已存在重复（需拦截）；
 * validate 为 false 表示可用。
 */
export function checkTicketFlowConfigClusterRepeat(params: {
  bk_biz_id: number;
  /** 集群 id 列表，逗号分隔 */
  cluster_ids: string;
  /** 当前编辑的子策略 id，仅编辑态传入（用于排除自身） */
  config_id?: number;
  /** 单据类型 */
  ticket_type: string;
}) {
  return http.get<
    Array<{
      id: number;
      validate: boolean;
    }>
  >(`${path}/check_ticket_flow_config_cluster_repeat/`, params);
}

/**
 * 校验按标签子策略的标签是否已在其他按标签子策略中（同一单据类型下不可重复）
 *
 * 响应中 validate 为 true 表示该标签已存在重复（需拦截）；
 * validate 为 false 表示可用。
 */
export function checkTicketFlowConfigClusterTagRepeat(params: {
  bk_biz_id: number;
  /** 标签条件列表 */
  cluster_tags: Array<{
    tag_key: string;
    tag_value: string;
  }>;
  /** 当前编辑的子策略 id，仅编辑态传入（用于排除自身） */
  config_id?: number;
  /** 单据类型 */
  ticket_type: string;
}) {
  return http.post<
    Array<{
      tag_key: string;
      tag_value: string;
      validate: boolean;
    }>
  >(`${path}/check_ticket_flow_config_cluster_tag_repeat/`, params);
}

export function getTicketStatus(params: { ticket_ids: string }) {
  return http.post<Record<string, string>>(`${path}/list_ticket_status/`, params, {
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
  conf_type: string;
  level_name: string;
  level_value: number;
  meta_cluster_type: string;
  version: string;
}) =>
  http.post<{
    bk_biz_id: number;
    conf_items: {
      conf_name: string;
      conf_value: string;
      op_type: string;
    }[];
    conf_type: string;
    level_name: string;
    level_value: number;
    meta_cluster_type: string;
    version: string;
  }>('/apis/configs/save_module_deploy_info/', params);

/**
 * 查询访问源列表
 */
export const getHostInAuthorize = (params: {
  bk_biz_id: string;
  keyword?: string;
  limit?: number;
  offset?: number;
  ticket_id: number;
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
export function revokeTicketFlow(params: { flow_id: number; ticketId: number }) {
  return http.post(`${path}/${params.ticketId}/revoke_flow/`, params);
}

/**
 * 批量待办处理
 */
export function ticketBatchProcessTodo(params: {
  action: 'APPROVE' | 'TERMINATE';
  operations: {
    params: Record<string, never>; // 暂时为空对象
    todo_id: number;
  }[];
}) {
  return http.post(`${path}/batch_process_todo/`, params);
}

/**
 * 获取集群下架待办列表
 */
export function ticketClusterDisableTodo(params: {
  db_type: DBTypes;
  is_assist: boolean;
  limit?: number;
  offset?: number;
}) {
  return http.get<ListBase<TicketClusterDisableTodoModel[]>>(`${path}/cluster_disable_todo/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new TicketClusterDisableTodoModel(item)),
  }));
}

/**
 * 获取集群下架待办汇总数量
 */
export function getClusterDisableCount() {
  return http.get<{
    to_assist: Record<DBTypes, number>;
    todo: Record<DBTypes, number>;
  }>(`${path}/get_cluster_disable_count/`);
}

/**
 * 主机处理待办汇总数量
 */
export function getHostTodoCount() {
  return http.get<{
    fault_count: number;
    recycle_count: number;
  }>(`${path}/get_host_todo_count/`);
}

export function checkDomainRepeat(params: {
  cluster_type: ClusterTypes;
  db_app_abbr: string; // 有db_module_id的集群类型，db_app_abbr 的值如果没有就按biz-{bk_biz_id}传
  db_module_id?: number;
  domains: string[];
}) {
  return http.post<
    {
      prefix: string;
      suffix: string;
      validate: boolean;
    }[]
  >(`${path}/check_domain_repeat/`, params);
}
