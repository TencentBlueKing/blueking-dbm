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

import http from './http';
import type { HostNode, ListBase } from './types/common';
import type {
  CapSepcs,
  CapSpecsParams,
  CitiyItem,
  ClusterOperateRecord,
  CreateAbbrParams,
  CreateModuleDeployInfo,
  CreateModuleParams,
  CreateModuleResult,
  FlowItem,
  FlowItemTodo,
  GetTicketParams,
  HostSpec,
  TicketItem,
  TicketNodesParams,
  TicketType,
} from './types/ticket';

/**
 * 查询服务器资源的城市信息
 */
export const getInfrasCities = () => http.get<CitiyItem[]>('/apis/infras/cities/');

/**
 * 服务器规格列表
 */
export const getInfrasHostSpecs = (params: { cityCode: string }) => http.get<HostSpec[]>(`/apis/infras/cities/${params.cityCode}/host_specs/`);

/**
 * redis 容量列表
 */
export const getCapSpecs = (params: CapSpecsParams & { cityCode: string }) => http.post<CapSepcs[]>('/apis/infras/cities/cap_specs/', params);

/**
 * 创建单据
 */
export const createTicket = (formData: object) => http.post<TicketItem>('/apis/tickets/', formData, { globalError: false })
  .then(res => res)
  .catch((e) => {
    const { code, data } = e;
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
              const res = await createTicket({ ...formData, ignore_duplication: true });
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

/**
 * 获取单据列表
 */
export const getTickets = (params: GetTicketParams = {}) => http.get<ListBase<TicketModel[]>>('/apis/tickets/', params).then(data => ({
  ...data,
  results: data.results.map(item => new TicketModel(item)),
}));

/**
 * 获取我的待办单据
 */
export const getTodoTickets = (params: GetTicketParams = {}) => http.get<ListBase<TicketModel[]>>('/apis/tickets/get_todo_tickets/', params).then(data => ({
  ...data,
  results: data.results.map(item => new TicketModel(item)),
}));

/**
 * 执行待办单据
 */
export const processTicketTodo = (params: {
  action: string,
  todo_id: number,
  ticket_id: number,
  params: object
}) => http.post<FlowItemTodo>(`/apis/tickets/${params.ticket_id}/process_todo/`, params);


/**
 * 获取单据详情
 */
export const getTicketDetails = (params: {
  id: number,
  is_reviewed?: number
}) => http.get<TicketModel>(`/apis/tickets/${params.id}/`, params).then(data => new TicketModel(data));

/**
 * 获取单据流程
 */
export const getTicketFlows = (params: { id: number }) => http.get<FlowItem[]>(`/apis/tickets/${params.id}/flows/`);

/**
 * 创建业务英文缩写
 */
export const createAppAbbr = (params: CreateAbbrParams & { id: number }) => http.post<CreateAbbrParams>(`/apis/cmdb/${params.id}/set_db_app_abbr/`, params);

/**
 * 创建模块
 */
export const createModules = (params: CreateModuleParams & { id: number }) => http.post<CreateModuleResult>(`/apis/cmdb/${params.id}/create_module/`, params);

/**
 * 保存模块配置
 */
export const saveModulesDeployInfo = (params: CreateModuleDeployInfo) => http.post<CreateModuleDeployInfo>('/apis/configs/save_module_deploy_info/', params);

/**
 * 获取单据类型
 */
export const getTicketTypes = (params?: { is_apply: 0 | 1 }) => http.get<TicketType[]>('/apis/tickets/flow_types/', params ?? {});

/**
 * 查询单据详情主机列表
 */
export const getTicketHostNodes = (params: TicketNodesParams) => http.get<HostNode[]>(`/apis/tickets/${params.id}/get_nodes/`, params);

/**
  * 查询访问源列表
  */
export const getHostInAuthorize = (params: {
  bk_biz_id: string,
  ticket_id: number
  limit?: number,
  offset?: number,
  keyword?: string
}) => http.get<{ hosts: HostNode[], ip_whitelist: {ip: string}[] }>(`/apis/mysql/bizs/${params.bk_biz_id}/permission/authorize/get_host_in_authorize/`, params)
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
  * 获取单据数量
  */
export const getTicketsCount = (params: { count_type: 'MY_TODO' | 'MY_APPROVE' }) => http.get<number>('/apis/tickets/get_tickets_count/', params);

/**
  * 查询集群变更事件
  */
export const getClusterOperateRecords = (params: Record<string, unknown> & { cluster_id: number }) => http.get<ListBase<ClusterOperateRecord[]>>('/apis/tickets/get_cluster_operate_records/', params);

/**
  * 查询集群实例变更事件
  */
export const getInstanceOperateRecords = (params: Record<string, unknown> & { instance_id: number }) => http.get<ListBase<ClusterOperateRecord[]>>('/apis/tickets/get_instance_operate_records/', params);

/**
  * 重试单据流程
  */
export const retryTicketFlow = (params: {
  ticketId: number,
  flow_id: number
}) => http.post(`/apis/tickets/${params.ticketId}/retry_flow/`, params);
