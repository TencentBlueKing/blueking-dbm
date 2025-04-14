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
import RedisDetailModel from '@services/model/redis/redis-detail';
import RedisInstanceModel from '@services/model/redis/redis-instance';
import RedisMachineModel from '@services/model/redis/redis-machine';
import type { HostNode, ListBase, ResourceTopo } from '@services/types';

import http from '../http';

const getRootPath = () => `/apis/redis/bizs/${window.PROJECT_CONFIG.BIZ_ID}/redis_resources`;

/**
 * 获取集群列表
 */
export function getRedisList(params: {
  bk_biz_id?: number;
  cluster_ids?: string;
  cluster_type?: string;
  domain?: string;
  exact_domain?: string;
  limit?: number;
  offset?: number;
}) {
  return http.get<ListBase<RedisModel[]>>(`${getRootPath()}/`, params).then((data) => ({
    ...data,
    results: data.results.map(
      (item) =>
        new RedisModel(
          Object.assign(item, {
            permission: Object.assign({}, item.permission, data.permission),
          }),
        ),
    ),
  }));
}

/**
 * 根据业务id获取集群列表
 */
export function getRedisListByBizId(
  params: {
    bk_biz_id?: number;
    cluster_ids?: number[] | number;
    domain?: string;
    limit?: number;
    offset?: number;
  } = {},
) {
  return http
    .get<ListBase<RedisModel[]>>(`/apis/redis/bizs/${params.bk_biz_id}/redis_resources/`, params)
    .then((data) => ({
      ...data,
      results: data.results.map((item) => new RedisModel(item)),
    }));
}

/**
 * 查询表格信息
 */
export function getRedisTableFields() {
  return http.get<
    {
      key: string;
      name: string;
    }[]
  >(`${getRootPath()}/get_table_fields/`);
}

/**
 * 获取集群实例列表
 */
export function getRedisInstances(params: {
  cluster_id?: number;
  cluster_type?: string;
  domain?: string;
  instance_address?: string;
  ip?: string;
  limit?: number;
  offset?: number;
  port?: number;
  role?: string;
  status?: string;
}) {
  return http.get<ListBase<RedisInstanceModel[]>>(`${getRootPath()}/list_instances/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new RedisInstanceModel(item)),
  }));
}

/**
 * 获取集群实例详情
 */
export function retrieveRedisInstance(params: {
  bk_biz_id: number;
  cluster_id?: number;
  instance_address: string;
  type: string;
}) {
  return http
    .get<RedisInstanceModel>(`${getRootPath()}/retrieve_instance/`, params)
    .then((data) => new RedisInstanceModel(data));
}

/**
 * 获取集群详情
 */
export function getRedisDetail(params: { id: number }) {
  return http.get<RedisDetailModel>(`${getRootPath()}/${params.id}/`).then((data) => new RedisDetailModel(data));
}

/**
 * 查询集群主机列表
 */
export function getRedisNodes(params: { bk_biz_id: string; cluster_id: string; db_type: string }) {
  return http.get<HostNode[]>(`${getRootPath()}/${params.cluster_id}/get_nodes/`, params);
}

/**
 * 获取集群密码
 */
export function getRedisPassword(params: { cluster_id: number }) {
  return http.get<{
    cluster_name: string;
    domain: string;
    password: string;
  }>(`${getRootPath()}/${params.cluster_id}/get_password/`);
}

/**
 * 获取集群拓扑
 */
export function getRedisTopoGraph(params: { cluster_id: number }) {
  return http.get<ResourceTopo>(`${getRootPath()}/${params.cluster_id}/get_topo_graph/`);
}

/**
 * 获取业务拓扑树
 */
export function getRedisResourceTree(params: { cluster_type: string }) {
  return http.get<BizConfTopoTreeModel[]>(`/apis/redis/bizs/${window.PROJECT_CONFIG.BIZ_ID}/resource_tree/`, params);
}

/**
 * 导出集群数据为 excel 文件
 */
export function exportRedisClusterToExcel(params: { cluster_ids?: number[] }) {
  return http.post<string>(`${getRootPath()}/export_cluster/`, params, { responseType: 'blob' });
}

/**
 * 导出实例数据为 excel 文件
 */
export function exportRedisInstanceToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${getRootPath()}/export_instance/`, params, { responseType: 'blob' });
}

// 获取集群列表
export const getRedisClusterList = async (params: {
  bk_biz_id: number;
  cluster_type?: string;
  domain?: string;
  region?: string;
}) =>
  http
    .get<ListBase<RedisModel[]>>(`/apis/redis/bizs/${params.bk_biz_id}/redis_resources/`, params)
    .then((data) => data.results.map((item) => new RedisModel(item)));

/**
 * 查询主机列表
 */
export function getRedisMachineList(params: {
  add_role_count?: boolean;
  bk_agent_id?: string;
  bk_city_name?: string;
  bk_cloud_id?: number;
  bk_host_id?: number;
  bk_os_name?: string;
  cluster_ids?: string;
  cluster_type?: string;
  creator?: string;
  extra?: number;
  instance_role?: string;
  ip?: string;
  limit?: number;
  machine_type?: string;
  offset?: number;
}) {
  return http.get<ListBase<RedisMachineModel[]>>(`${getRootPath()}/list_machines/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new RedisMachineModel(item)),
  }));
}
