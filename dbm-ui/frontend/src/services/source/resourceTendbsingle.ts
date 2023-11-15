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

import { useGlobalBizs } from '@stores';

import http from '../http';
import type {
  GetResourcesParams,
  InstanceDetails,
  InstanceDetailsParams,
  ResourceInstance,
  ResourceItem,
  ResourceTopo,
  ResourceTopoParams,
  TableFieldsItem,
} from '../types/clusters';
import type { ListBase } from '../types/common';

const { currentBizId } = useGlobalBizs();

const path = `/apis/mysql/bizs/${currentBizId}/tendbsingle_resources`;

/**
 * 查询资源列表
 */
export const getResources = (params: GetResourcesParams & { dbType: string }) => http.get<ListBase<ResourceItem[]>>(`${path}/`, params);

/**
 * 查询表格信息
 */
export const getTableFields = () => http.get<TableFieldsItem[]>(`${path}/get_table_fields/`);

/**
 * 获取集群实例列表
 */
export const getResourceInstances = (params: Record<string, any>) => http.get<ListBase<ResourceInstance[]>>(`${path}/list_instances/`, params);

/**
 * 获取集群实例详情
 */
export const getResourceInstanceDetails = (params: InstanceDetailsParams & { dbType: string }) => http.get<InstanceDetails>(`${path}/retrieve_instance/`, params);

/**
 * 获取集群详情
 */
export const getResourceDetails = (params: { id: number }) => http.get<ResourceItem>(`${path}/${params.id}/`);

/**
 * 获取集群拓扑
 */
export const getResourceTopo = (params: ResourceTopoParams & { dbType: string }) => http.get<ResourceTopo>(`${path}/${params.resource_id}/get_topo_graph/`);
