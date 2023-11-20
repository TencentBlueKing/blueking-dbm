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

import { useGlobalBizs } from '@stores';

import http from '../http';
import type { ListBase } from '../types';
import type {
  GetResourcesParams,
  InstanceDetails,
  InstanceDetailsParams,
  ResourceInstance,
  ResourceItem,
  ResourceTopo,
  TableFieldsItem,
} from '../types/clusters';

const { currentBizId } = useGlobalBizs();

const path = `/apis/mysql/bizs/${currentBizId}/spider_resources`;

/**
 * 获取 spider 集群列表
 */
export const getSpiderList = function (params: Record<string, any>) {
  return http.get<ListBase<SpiderModel[]>>(`${path}/`, params).then(data => ({
    ...data,
    results: data.results.map((item: SpiderModel) => new SpiderModel(item)),
  }));
};

/**
 * 查询资源列表
 */
export const getResources = function (params: GetResourcesParams & { dbType: string }) {
  return http.get<ListBase<ResourceItem[]>>(`${path}/`, params);
};

/**
 * 查询表格信息
 */
export const getSpiderTableFields = function () {
  return http.get<TableFieldsItem[]>(`${path}/get_table_fields/`);
};

/**
 * 获取集群实例列表
 */
export const getSpiderInstanceList = function (params: Record<string, any>) {
  return http.get<ListBase<ResourceInstance[]>>(`${path}/list_instances/`, params);
};

/**
 * 获取集群实例详情
 */
export const retrieveSpiderInstance = function (params: InstanceDetailsParams & { dbType: string }) {
  return http.get<InstanceDetails>(`${path}/retrieve_instance/`, params);
};

/**
 * 获取集群详情
 */
export const getSpiderDetail = function (params: { clusterId: number }) {
  return http.get<SpiderModel>(`${path}/${params.clusterId}/`).then(data => new SpiderModel(data));
};

/**
 * 获取集群拓扑
 */
export const getSpiderTopoGraph = function (params: { cluster_id: number }) {
  return http.get<ResourceTopo>(`${path}/${params.cluster_id}/get_topo_graph/`);
};
