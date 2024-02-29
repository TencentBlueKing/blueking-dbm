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

import SqlServerClusterDetailModel from '@services/model/sqlserver/sqlserver-cluster-detail';
import SqlServerClusterListModel from '@services/model/sqlserver/sqlserver-ha-cluster';

import { useGlobalBizs } from '@stores';

import http from '../http';
import type {
  ListBase,
  ResourceTopo,
} from '../types';

const { currentBizId } = useGlobalBizs();

const path = `/apis/sqlserver/bizs/${currentBizId}/sqlserver_single_resources`;

/**
 * 获取集群列表
 */
export function getSingleClusterList(params: {
  limit?: number,
  offset?: number,
}) {
  return http.get<ListBase<SqlServerClusterListModel[]>>(`${path}/`, params)
    .then(data => ({
      ...data,
      results: data.results.map(item => new SqlServerClusterListModel(item)),
    }));
}

/**
 * 获取集群详情
 */
export function getSingleClusterDetail(params: { cluster_id: number }) {
  return http.get<SqlServerClusterDetailModel>(`${path}/${params.cluster_id}/`)
    .then(data => new SqlServerClusterDetailModel(data));
}

/**
 * 获取集群拓扑
 */
export function getSingleClusterTopoGraph(params: { cluster_id: number }) {
  return http.get<ResourceTopo>(`${path}/${params.cluster_id}/get_topo_graph/`);
}

/**
 * 导出数据为 excel 文件
 */
export function exportSqlServerSingleClusterToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${path}/export_instance/`, params, { responseType: 'blob' });
}

/**
 * 获取集群实例列表
 */
export const getSqlServerInstanceList = function () {
  return http.get<ListBase<any[]>>(`${path}/list_instances/`);
};
