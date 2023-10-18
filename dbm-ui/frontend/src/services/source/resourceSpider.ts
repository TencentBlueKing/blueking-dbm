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

import SpiderModel from '@services/model/spider/spider';
import TendbClusterModel from '@services/model/spider/tendbCluster';
import TendbInstanceModel from '@services/model/spider/tendbInstance';

import { useGlobalBizs } from '@stores';

import http from '../http';
import type {
  ClusterPassword,
  ClusterPasswordParams,
  GetClusterHostNodesRequestParam,
  GetResourcesParams,
  InstanceDetails,
  InstanceDetailsParams,
  InstanceInfos,
  MySQLClusterInfos,
  ResourceInstance,
  ResourceItem, ResourceParams,
  ResourcesResult,
  ResourceTopo,
  ResourceTopoParams,
  TableFieldsItem,
  TableFieldsParams,
} from '../types/clusters';
import type { ListBase } from '../types/common';

const { currentBizId } = useGlobalBizs();

const path = `/apis/mysql/bizs/${currentBizId}/spider_resources`;

/**
 * 获取 spider 集群列表
 */
export const getList = (params: Record<string, any> = {}) => http.get<{
    count: number,
    results: TendbClusterModel[]
  }>(`${path}/`, params)
  .then(res => ({
    ...res,
    results: res.results.map(data => new TendbClusterModel(data)),
  }));

/**
 * 查询表格信息
 */
export const getTableFields = () => http.get<TableFieldsItem[]>(`${path}/get_table_fields/`);

/**
 * 获取 spider 实例列表
 */
export const getInstances = (params: Record<string, any>) => http.get<ListBase<TendbInstanceModel[]>>(`${path}/list_instances/`, params)
  .then(res => ({
    ...res,
    results: res.results.map(data => new TendbInstanceModel(data)),
  }));

/**
 * 获取 spider 实例详情
 */
export const getInstanceDetails = (params: {
  instance_address: string,
  cluster_id: number
}) => http.get<TendbInstanceModel>(`${path}/retrieve_instance/`, params);

/**
 * 获取 spider 集群详情
 */
export const getDetails = (params: { id: number }) => http.get<TendbClusterModel>(`${path}/${params.id}/`);

/**
 * 获取集群拓扑
 */
export const getResourceTopo = (params: ResourceTopoParams) => http.get<ResourceTopo>(`${path}/${params.resource_id}/get_topo_graph/`);

export const getSpiderList = (params: Record<string, any>) => http.get<ListBase<SpiderModel[]>>(`${path}/`, params)
  .then(data => ({
    ...data,
    results: data.results.map((item: SpiderModel) => new SpiderModel(item)),
  }));

export const getDetail = (params: { id: number }) => http.get<SpiderModel>(`${path}/${params.id}/`)
  .then(data => new SpiderModel(data));
