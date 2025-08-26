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
import MongodbModel from '@services/model/mongodb/mongodb';
import MongodbDetailModel from '@services/model/mongodb/mongodb-detail';
import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';
import MongodbInstanceDetailModel from '@services/model/mongodb/mongodb-instance-detail';
import MongodbMachineModel from '@services/model/mongodb/mongodb-machine';
import type { ListBase } from '@services/types';

import { useGlobalBizs } from '@stores';

import http from '../http';

const { currentBizId } = useGlobalBizs();

const getRootPath = () => `/apis/mongodb/bizs/${window.PROJECT_CONFIG.BIZ_ID}/mongodb_resources`;

interface RelatedCluster {
  cluster_id: number;
  cluster_info: ClusterInfo;
  related_clusters: ClusterInfo[];
}

interface ClusterInfo {
  alias: string;
  bk_biz_id: number;
  bk_cloud_id: number;
  cluster_name: string;
  cluster_type: string;
  creator: string;
  db_module_id: number;
  disaster_tolerance_level: string;
  id: number;
  immute_domain: string;
  major_version: string;
  master_domain: string;
  name: string;
  phase: string;
  region: string;
  status: string;
  time_zone: string;
  updater: string;
}

/**
 * 获取Mongo集群
 */
export function getMongoList(params: {
  cluster_ids?: string;
  cluster_type?: string;
  creator?: string;
  db_module_id?: number;
  domain?: string;
  domains?: string;
  exact_domain?: string;
  id?: number;
  ip?: string;
  limit?: number;
  name?: string;
  offset?: number;
  region?: string;
  version?: string;
}) {
  return http.get<ListBase<MongodbModel[]>>(`${getRootPath()}/`, params).then((data) => ({
    ...data,
    results: data.results.map(
      (item) =>
        new MongodbModel(
          Object.assign(item, {
            permission: Object.assign({}, item.permission, data.permission),
          }),
        ),
    ),
  }));
}

/**
 * 获取Mongo拓扑
 */
export function getMongoTopoList(params: {
  cluster_ids?: string;
  cluster_type?: string;
  creator?: string;
  db_module_id?: number;
  domain?: string;
  exact_domain?: string;
  id?: number;
  ip?: string;
  limit?: number;
  name?: string;
  offset?: number;
  region?: string;
  version?: string;
}) {
  return http
    .get<ListBase<MongodbModel[]>>(`${getRootPath()}/`, params)
    .then((data) => data.results.map((item) => new MongodbModel(item)));
}

/**
 * 查询Mongo集群详情
 */
export function getMongoClusterDetails(params: { cluster_id: number }) {
  return http
    .get<MongodbDetailModel>(`${getRootPath()}/${params.cluster_id}/`)
    .then((data) => new MongodbDetailModel(data));
}

/**
 * 查询Mongo拓扑图
 */
export function getMongoClustersTopoGraph(params: { cluster_id: number }) {
  return http.get(`${getRootPath()}/${params.cluster_id}/get_topo_graph/`);
}

/**
 * 获取Mongo集群 table 信息
 */
export function getMongoTableFields(params: { limit?: number; offset?: number }) {
  return http.get(`${getRootPath()}/get_table_fields/`, params);
}

/**
 * 查询Mongo集群实例列表
 */
export function getMongoInstancesList(params: {
  address?: string;
  cluster_id?: number;
  cluster_type?: string;
  domain?: string;
  extra?: number;
  instance_address?: string;
  ip?: string;
  limit?: number;
  offset?: number;
  port?: number;
  role?: string;
  status?: string;
}) {
  return http.get<ListBase<MongodbInstanceModel[]>>(`${getRootPath()}/list_instances/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new MongodbInstanceModel(item)),
  }));
}

/**
 * 查询Mongo集群实例详情
 */
export function retrieveMongoInstanceDetail(params: {
  cluster_id?: number;
  instance?: string;
  ip?: string;
  limit?: number;
  offset?: number;
  port?: string;
}) {
  return http
    .get<MongodbInstanceDetailModel>(`${getRootPath()}/retrieve_instance/`, params)
    .then((data) => new MongodbInstanceDetailModel(data));
}

/**
 * 获取Mongo角色列表
 */
export function getMongoRoleList(params: { limit?: number; offset?: number }) {
  return http.get<string[]>(`${getRootPath()}/get_instance_role/`, params);
}

/**
 * 查询机器列表
 */
export function getMongodbMachineList(params: {
  bk_agent_id?: string;
  bk_cloud_id?: number;
  bk_host_id?: number;
  bk_os_name?: string;
  cluster_type?: string;
  creator?: string;
  ip?: string;
  limit?: number;
  machine_type?: string;
  offset?: number;
}) {
  return http.get<ListBase<MongodbMachineModel[]>>(`${getRootPath()}/list_machines/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new MongodbMachineModel(item)),
  }));
}

/**
 * 导出Mongo集群数据为 excel 文件
 */
export function exportMongodbClusterToExcel(params: { cluster_ids?: number[]; cluster_types?: string }) {
  return http.post<string>(`${getRootPath()}/export_cluster/`, params, { responseType: 'blob' });
}

/**
 * 导出Mongo实例数据为 excel 文件
 */
export function exportMongodbInstanceToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${getRootPath()}/export_instance/`, params, { responseType: 'blob' });
}

/**
 * 获取业务拓扑树
 */
export function getMongoDBResourceTree(params: { cluster_type: string }) {
  return http.get<BizConfTopoTreeModel[]>(`/apis/mongodb/bizs/${currentBizId}/resource_tree/`, params);
}

/**
 * 通过集群查询同机关联集群
 */
export function getRelatedClustersByClusterIds(params: { cluster_ids: number[] }) {
  return http.post<RelatedCluster[]>(
    `/apis/mongodb/bizs/${currentBizId}/cluster/find_related_clusters_by_cluster_ids/`,
    params,
  );
}
