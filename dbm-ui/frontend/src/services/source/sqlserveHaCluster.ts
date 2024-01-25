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
import SqlServerClusterListModel from '../model/sqlserver/sqlserver-cluster';
import SqlserverClusterDetailModel from '../model/sqlserver/sqlserver-cluster-detail';
import type {
  ListBase,
  ResourceTopo,
} from '../types';

const { currentBizId } = useGlobalBizs();

const path = `/apis/sqlserver/bizs/${currentBizId}/sqlserver_ha_resources`;

/**
 * 获取集群列表
 */
export function getHaClusterList(params: {
  limit?: number,
  offset?: number,
}) {
<<<<<<< HEAD
  return http.get<ListBase<SqlServerClusterListModel[]>>(`${path}/`, params)
    .then(data => ({
      ...data,
      results: data.results.map(item => new SqlServerClusterListModel(item)),
    }));
=======
  return http.get<ListBase<SqlServerClusterListModel[]>>(`${path}/`, params).then(data => ({
    ...data,
    results: data.results.map(item => new SqlServerClusterListModel(item)),
  }));
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e
}

/**
 * 获取集群详情
 */
export function getHaClusterDetail(params: { cluster_id: number }) {
<<<<<<< HEAD
  return http.get<SqlserverClusterDetailModel>(`${path}/${params.cluster_id}/`)
    .then(data => new SqlserverClusterDetailModel(data));
=======
  return http.get<SqlserverClusterDetailModel>(`${path}/${params.cluster_id}/`).then(data => new SqlserverClusterDetailModel(data));
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e
}

/**
 * 获取集群拓扑
 */
export function getHaClusterTopoGraph(params: { cluster_id: number }) {
  return http.get<ResourceTopo>(`${path}/${params.cluster_id}/get_topo_graph/`);
}

/**
 * 导出数据为 excel 文件
 */
export function exportSqlserverHaClusterToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${path}/export_instance/`, params, { responseType: 'blob' });
}
