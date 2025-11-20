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

import OracleHaModel from '@services/model/oracle/oracle-ha';
import OracleHaDetailModel from '@services/model/oracle/oracle-ha-detail';
import OracleHaInstanceModel from '@services/model/oracle/oracle-ha-instance';
import OracleHaMachineModel from '@services/model/oracle/oracle-ha-machine';
import type { ListBase, ResourceTopo } from '@services/types';

import http from '../http';

const getPath = () => `/apis/oracle/bizs/${window.PROJECT_CONFIG.BIZ_ID}/oracleha_resources`;

/**
 * 获取集群列表
 */
export function getOracleHaClusterList(params: {
  cluster_ids?: string;
  creator?: string;
  domain?: string;
  id?: number;
  ip?: string;
  limit?: number;
  name?: string;
  offset?: number;
}) {
  return http.get<ListBase<OracleHaModel[]>>(`${getPath()}/`, params).then((data) => ({
    ...data,
    results: data.results.map(
      (item) => new OracleHaModel(Object.assign({}, item, Object.assign(item.permission, data.permission))),
    ),
  }));
}

/**
 * 获取集群详情
 */
export function getOracleHaClusterDetail(params: { id: number }) {
  return http.get<OracleHaDetailModel>(`${getPath()}/${params.id}/`).then((data) => new OracleHaDetailModel(data));
}

/**
 * 获取集群拓扑
 */
export function getOracleHaClusterTopoGraph(params: { cluster_id: number }) {
  return http.get<ResourceTopo>(`${getPath()}/${params.cluster_id}/get_topo_graph/`);
}

/**
 * 导出集群数据为 excel 文件
 */
export function exportOracleHaClusterToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${getPath()}/export_cluster/`, params, { responseType: 'blob' });
}

/**
 * 导出实例数据为 excel 文件
 */
export function exportOracleHaInstanceToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${getPath()}/export_instance/`, params, { responseType: 'blob' });
}

/**
 * 获取集群实例列表
 */
export function getOracleHaInstanceList(params: {
  bk_biz_id?: number;
  cluster_id?: number;
  limit?: number;
  offset?: number;
  role?: string;
}) {
  return http.get<ListBase<OracleHaInstanceModel[]>>(`${getPath()}/list_instances/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new OracleHaInstanceModel(item)),
  }));
}

/**
 * 获取集群实例详情
 */
export function retrieveOracleHaInstance(params: {
  cluster_id?: number;
  dbType?: string;
  instance?: string;
  type?: string;
}) {
  return http
    .get<OracleHaInstanceModel>(`${getPath()}/retrieve_instance/`, params)
    .then((res) => new OracleHaInstanceModel(res));
}

/**
 * 查询主机列表
 */
export function getOracleHaMachineList(params: {
  bk_agent_id?: string;
  bk_cloud_id?: number;
  bk_host_id?: number;
  bk_os_name?: string;
  creator?: string;
  instance_role?: string;
  ip?: string;
  limit?: number;
  machine_type?: string;
  offset?: number;
}) {
  return http.get<ListBase<OracleHaMachineModel[]>>(`${getPath()}/list_machines/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new OracleHaMachineModel(item)),
  }));
}
