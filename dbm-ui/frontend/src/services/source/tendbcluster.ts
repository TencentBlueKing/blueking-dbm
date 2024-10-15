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

import TendbclusterModel from '@services/model/tendbcluster/tendbcluster';
import TendbclusterDetailModel from '@services/model/tendbcluster/tendbcluster-detail';
import TendbclusterInstanceModel from '@services/model/tendbcluster/tendbcluster-instance';
import TendbclusterMachineModel from '@services/model/tendbcluster/tendbcluster-machine';
import type { ListBase, ResourceTopo } from '@services/types';

import http from '../http';

const getRootPath = () => `/apis/mysql/bizs/${window.PROJECT_CONFIG.BIZ_ID}/spider_resources`;

/**
 * 获取 TendbCluster 集群列表
 */
export function getTendbClusterList(params: {
  limit?: number;
  offset?: number;
  id?: number;
  name?: string;
  ip?: string;
  domain?: string;
  exact_domain?: string;
  creator?: string;
  version?: string;
  cluster_ids?: number[];
  db_module_id?: number;
  region?: string;
}) {
  return http.get<ListBase<TendbclusterModel[]>>(`${getRootPath()}/`, params).then((data) => ({
    ...data,
    results: data.results.map(
      (item) =>
        new TendbclusterModel(
          Object.assign(item, {
            permission: Object.assign({}, item.permission, data.permission),
          }),
        ),
    ),
  }));
}

/**
 * 获取 TendbCluster 集群列表
 */
export function getTendbClusterFlatList(params: {
  limit?: number;
  offset?: number;
  id?: number;
  name?: string;
  ip?: string;
  domain?: string;
  exact_domain?: string;
  creator?: string;
  version?: string;
  cluster_ids?: number[];
  db_module_id?: number;
  region?: string;
}) {
  return http.get<ListBase<TendbclusterModel[]>>(`${getRootPath()}/`, params).then((data) =>
    data.results.map(
      (item) =>
        new TendbclusterModel(
          Object.assign(item, {
            permission: Object.assign({}, item.permission, data.permission),
          }),
        ),
    ),
  );
}

/**
 * 获取 TendbCluster 从集群列表
 */
export function getTendbSlaveClusterList(params: { limit?: number; offset?: number; spider_slave_exist?: boolean }) {
  params.spider_slave_exist = true;
  return http.get<ListBase<TendbclusterModel[]>>(`${getRootPath()}/`, params).then((data) => ({
    ...data,
    results: data.results.map(
      (item) =>
        new TendbclusterModel(
          Object.assign(item, {
            master_domain: item.slave_domain,
            permission: Object.assign({}, item.permission, data.permission),
          }),
        ),
    ),
  }));
}

/**
 * 根据业务 id 获取 spider 集群列表
 */
export function getTendbclusterListByBizId(params: {
  bk_biz_id: number;
  limit?: number;
  offset?: number;
  id?: number;
  name?: string;
  ip?: string;
  domain?: string;
  creator?: string;
  version?: string;
  cluster_ids?: number[];
  db_module_id?: number;
  region?: string;
}) {
  return http
    .get<ListBase<TendbclusterModel[]>>(`/apis/mysql/bizs/${params.bk_biz_id}/spider_resources/`, params)
    .then((data) => ({
      ...data,
      results: data.results.map((item: TendbclusterModel) => new TendbclusterModel(item)),
    }));
}

/**
 * 获取集群实例列表
 */
export function getTendbclusterInstanceList(params: Record<string, any>) {
  return http.get<ListBase<TendbclusterInstanceModel[]>>(`${getRootPath()}/list_instances/`, params).then((res) => ({
    ...res,
    results: res.results.map((data) => new TendbclusterInstanceModel(data)),
  }));
}

/**
 * 获取集群详情
 */
export function getTendbclusterDetail(params: { id: number }) {
  return http
    .get<TendbclusterDetailModel>(`${getRootPath()}/${params.id}/`)
    .then((data) => new TendbclusterDetailModel(data));
}

/**
 * 获取集群拓扑
 */
export function getTendbclusterTopoGraph(params: { cluster_id: number }) {
  return http.get<ResourceTopo>(`${getRootPath()}/${params.cluster_id}/get_topo_graph/`);
}

/**
 * 导出集群数据为 excel 文件
 */
export function exportTendbclusterToExcel(params: { cluster_ids?: number[] }) {
  return http.post<string>(`${getRootPath()}/export_cluster/`, params, { responseType: 'blob' });
}

/**
 * 导出实例数据为 excel 文件
 */
export function exportTendbclusterInstanceToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${getRootPath()}/export_instance/`, params, { responseType: 'blob' });
}

/**
 * 查询主机列表
 */
export function getTendbclusterMachineList(params: {
  limit?: number;
  offset?: number;
  bk_host_id?: number;
  ip?: string;
  machine_type?: string;
  bk_os_name?: string;
  bk_cloud_id?: number;
  bk_agent_id?: string;
  instance_role?: string;
  spider_role?: string;
  creator?: string;
}) {
  return http.get<ListBase<TendbclusterMachineModel[]>>(`${getRootPath()}/list_machines/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new TendbclusterMachineModel(item)),
  }));
}

/**
 * 获取 spider 实例详情
 */
export const getTendbclusterInstanceDetail = (params: { instance_address: string; cluster_id: number }) =>
  http.get<TendbclusterInstanceModel>(`${getRootPath()}/retrieve_instance/`, params);

/**
 * 获取集群primary关系映射
 */
export const getTendbclusterPrimary = (params: { cluster_ids: number[] }) =>
  http.post<
    {
      cluster_id: number;
      primary: string;
    }[]
  >(`${getRootPath()}/get_cluster_primary/`, params);
