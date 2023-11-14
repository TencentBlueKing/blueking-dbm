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

import BizConfTopoTreeModel from '@services/model/config/biz-conf-topo-tree';
import RedisModel from '@services/model/redis/redis';

import { useGlobalBizs } from '@stores';

import http from '../http';
import type {
  ClusterPasswordParams,
  InstanceDetails,
  InstanceDetailsParams,
  ResourceInstance,
  ResourceRedisItem,
  ResourceTopo,
  ResourceTopoParams,
  TableFieldsItem,
} from '../types/clusters';
import type {
  HostNode,
  ListBase,
} from '../types/common';

const { currentBizId } = useGlobalBizs();

const path = `/apis/redis/bizs/${currentBizId}/redis_resources`;

/**
 * 获取集群列表
 */
export const getRedisList = function (params: {
  limit?: number,
  offset?: number,
  type?: string,
  dbType?: string,
  cluster_ids?: number[] | number,
  domain?: string,
  bk_biz_id?: number,
} = {}) {
  return http.get<ListBase<RedisModel[]>>(`${path}/`, params).then(data => ({
    ...data,
    results: data.results.map(item => new RedisModel(item)),
  }));
};

/**
 * 查询表格信息
 */
export const getRedisTableFields = function () {
  return http.get<TableFieldsItem[]>(`${path}/get_table_fields/`);
};

/**
 * 获取集群实例列表
 */
export const getRedisInstances = function (params: Record<string, any>) {
  return http.get<ListBase<ResourceInstance[]>>(`${path}/list_instances/`, params);
};

/**
 * 获取集群实例详情
 */
export const retrieveRedisInstance = function (params: InstanceDetailsParams & { dbType: string }) {
  return http.get<InstanceDetails>(`${path}/retrieve_instance/`, params);
};

/**
 * 获取集群详情
 */
export const getRedisDetail = function (params: {
  bk_biz_id: number,
  id: number,
  type: string
  dbType: string
}) {
  return http.get<ResourceRedisItem>(`${path}/${params.id}/`);
};

/**
 * 查询集群主机列表
 */
export const getRedisNodes = function (params: {
  db_type: string;
  bk_biz_id: string;
  cluster_id: string;
}) {
  return http.get<HostNode[]>(`${path}/${params.cluster_id}/get_nodes/`, params);
};

/**
 * 获取集群密码
 */
export const getRedisPassword = function (params: ClusterPasswordParams) {
  return http.get<{
    cluster_name: string,
    domain: string,
    password: string
  }>(`${path}/${params.cluster_id}/get_password/`);
};

/**
 * 获取集群拓扑
 */
export const getRedisTopoGraph = function (params: ResourceTopoParams & { dbType: string }) {
  return http.get<ResourceTopo>(`${path}/${params.resource_id}/get_topo_graph/`);
};

/**
 * 获取业务拓扑树
 */
export const getRedisResourceTree = function (params: { cluster_type: string }) {
  return http.get<BizConfTopoTreeModel[]>(`/apis/redis/bizs/${currentBizId}/resource_tree/`, params);
};
