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

import SqlServerInstanceModel from '@services/model/sqlserver/sqlserver-ha-instance';
import SqlServerSingleModel from '@services/model/sqlserver/sqlserver-single';
import SqlServerSingleDetailModel from '@services/model/sqlserver/sqlserver-single-detail';
import type { ListBase, ResourceTopo } from '@services/types';

import http from '../http';

const getPath = () => `/apis/sqlserver/bizs/${window.PROJECT_CONFIG.BIZ_ID}/sqlserver_single_resources`;

/**
 * 获取集群列表
 */
export function getSingleClusterList(params: { limit?: number; offset?: number }) {
  return http.get<ListBase<SqlServerSingleModel[]>>(`${getPath()}/`, params).then((data) => ({
    ...data,
    results: data.results.map(
      (item) => new SqlServerSingleModel(Object.assign({}, item, Object.assign(item.permission, data.permission))),
    ),
  }));
}

/**
 * 获取集群详情
 */
export function getSingleClusterDetail(params: { id: number }) {
  return http
    .get<SqlServerSingleDetailModel>(`${getPath()}/${params.id}/`)
    .then((data) => new SqlServerSingleDetailModel(data));
}

/**
 * 获取集群拓扑
 */
export function getSingleClusterTopoGraph(params: { cluster_id: number }) {
  return http.get<ResourceTopo>(`${getPath()}/${params.cluster_id}/get_topo_graph/`);
}

/**
 * 导出数据为 excel 文件
 */
export function exportSqlServerSingleClusterToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${getPath()}/export_instance/`, params, { responseType: 'blob' });
}

/**
 * 获取集群实例列表
 */
export function getSqlServerInstanceList(params: {
  offset?: number;
  limit?: number;
  bk_biz_id?: number;
  cluster_id?: number;
  role?: string;
}) {
  return http.get<ListBase<SqlServerInstanceModel[]>>(`${getPath()}/list_instances/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new SqlServerInstanceModel(item)),
  }));
}
