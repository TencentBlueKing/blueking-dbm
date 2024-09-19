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
import SpiderMachineModel from '@services/model/spider/spiderMachine';
import TendbClusterModel from '@services/model/spider/tendbCluster';
import TendbInstanceModel from '@services/model/spider/tendbInstance';

import http from '../http';
import type { ListBase, ResourceTopo } from '../types';

const getRootPath = () => `/apis/mysql/bizs/${window.PROJECT_CONFIG.BIZ_ID}/spider_resources`;

/**
 * 获取 TendbCluster 集群列表
 */
export function getTendbClusterList(params: Record<string, any> = {}) {
  return http.get<ListBase<TendbClusterModel[]>>(`${getRootPath()}/`, params).then((data) => ({
    ...data,
    results: data.results.map(
      (item) =>
        new TendbClusterModel(
          Object.assign(item, {
            permission: Object.assign({}, item.permission, data.permission),
          }),
        ),
    ),
  }));
}

/**
 * 获取 spider 集群列表
 */
export function getSpiderList(params: {
  limit?: number;
  offset?: number;
  id?: number;
  name?: string;
  ip?: string;
  domain?: string;
  exact_domain?: string;
  creator?: string;
  version?: string;
  cluster_ids?: string | number;
  db_module_id?: number;
  region?: string;
}) {
  return http.get<ListBase<SpiderModel[]>>(`${getRootPath()}/`, params).then((data) => ({
    ...data,
    results: data.results.map((item: SpiderModel) => new SpiderModel(item)),
  }));
}

/**
 * 根据业务 id 获取 spider 集群列表
 */
export function getSpiderListByBizId(params: {
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
    .get<ListBase<SpiderModel[]>>(`/apis/mysql/bizs/${params.bk_biz_id}/spider_resources/`, params)
    .then((data) => ({
      ...data,
      results: data.results.map((item: SpiderModel) => new SpiderModel(item)),
    }));
}

/**
 * 查询资源列表
 */
export function getResources(params: {
  bk_biz_id: number;
  limit: number;
  offset: number;
  type: string;
  cluster_ids?: number[] | number;
  dbType: string;
}) {
  return http.get<ListBase<TendbClusterModel[]>>(`${getRootPath()}/`, params);
}

/**
 * 根据业务 ID 查询资源列表
 */
export function getResourcesByBizId(params: {
  bk_biz_id: number;
  limit: number;
  offset: number;
  type: string;
  cluster_ids?: number[] | number;
  dbType: string;
}) {
  return http.get<ListBase<TendbClusterModel[]>>(`/apis/mysql/bizs/${params.bk_biz_id}/spider_resources/`, params);
}

/**
 * 查询表格信息
 */
export function getSpiderTableFields() {
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
export function getSpiderInstanceList(params: Record<string, any>) {
  return http.get<ListBase<TendbInstanceModel[]>>(`${getRootPath()}/list_instances/`, params).then((res) => ({
    ...res,
    results: res.results.map((data) => new TendbInstanceModel(data)),
  }));
}

/**
 * 获取集群详情
 */
export function getSpiderDetail(params: { id: number }) {
  return http.get<SpiderModel>(`${getRootPath()}/${params.id}/`).then((data) => new SpiderModel(data));
}

/**
 * 获取集群拓扑
 */
export function getSpiderTopoGraph(params: { cluster_id: number }) {
  return http.get<ResourceTopo>(`${getRootPath()}/${params.cluster_id}/get_topo_graph/`);
}

/**
 * 导出集群数据为 excel 文件
 */
export function exportSpiderClusterToExcel(params: { cluster_ids?: number[] }) {
  return http.post<string>(`${getRootPath()}/export_cluster/`, params, { responseType: 'blob' });
}

/**
 * 导出实例数据为 excel 文件
 */
export function exportSpiderInstanceToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${getRootPath()}/export_instance/`, params, { responseType: 'blob' });
}

/**
 * 查询主机列表
 */
export function getSpiderMachineList(params: {
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
  return http.get<ListBase<SpiderMachineModel[]>>(`${getRootPath()}/list_machines/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new SpiderMachineModel(item)),
  }));
}

/**
 * 获取 spider 集群详情
 * @param id 集群 ID
 */
export const getSpiderDetails = (params: { id: number }) =>
  http.get<TendbClusterModel>(`${getRootPath()}/${params.id}/`);

/**
 * 获取 spider 实例详情
 */
export const getSpiderInstanceDetails = (params: { instance_address: string; cluster_id: number }) =>
  http.get<TendbInstanceModel>(`${getRootPath()}/retrieve_instance/`, params);

export const getList = function (params: Record<string, any>) {
  return http.get<ListBase<SpiderModel[]>>(`${getRootPath()}/`, params).then((data) => ({
    ...data,
    results: data.results.map((item: SpiderModel) => new SpiderModel(item)),
  }));
};

export const getDetail = function (params: { id: number }) {
  return http.get<SpiderModel>(`${getRootPath()}/${params.id}/`).then((data) => new SpiderModel(data));
};
