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

import OracleSingleMachineModel from '@services/model/oracle/oracle-ha-machine';
import OracleSingleModel from '@services/model/oracle/oracle-single';
import OracleSingleDetailModel from '@services/model/oracle/oracle-single-detail';
import OracleSingleInstanceModel from '@services/model/oracle/oracle-single-instance';
import type { ListBase, ResourceTopo } from '@services/types';

import http from '../http';

const getPath = () => `/apis/oracle/bizs/${window.PROJECT_CONFIG.BIZ_ID}/oraclesingle_resources`;

/**
 * 获取集群列表
 */
export function getOracleSingleClusterList(params: {
  cluster_ids?: string;
  creator?: string;
  domain?: string;
  id?: number;
  ip?: string;
  limit?: number;
  name?: string;
  offset?: number;
}) {
  return http.get<ListBase<OracleSingleModel[]>>(`${getPath()}/`, params).then((data) => ({
    ...data,
    results: data.results.map(
      (item) => new OracleSingleModel(Object.assign({}, item, Object.assign(item.permission, data.permission))),
    ),
  }));
}

/**
 * 获取集群详情
 */
export function getOracleSingleClusterDetail(params: { id: number }) {
  return http
    .get<OracleSingleDetailModel>(`${getPath()}/${params.id}/`)
    .then((data) => new OracleSingleDetailModel(data));
}

/**
 * 获取集群拓扑
 */
export function getOracleSingleClusterTopoGraph(params: { cluster_id: number }) {
  return http.get<ResourceTopo>(`${getPath()}/${params.cluster_id}/get_topo_graph/`);
}

/**
 * 导出数据为 excel 文件
 */
export function exportOracleSingleClusterToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${getPath()}/export_instance/`, params, { responseType: 'blob' });
}

/**
 * 导出实例数据为 excel 文件
 */
export function exportOracleSingleInstanceToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${getPath()}/export_instance/`, params, { responseType: 'blob' });
}

/**
 * 获取集群实例列表
 */
export function getOracleSingleInstanceList(params: {
  bk_biz_id?: number;
  cluster_id?: number;
  limit?: number;
  offset?: number;
  role?: string;
}) {
  return http.get<ListBase<OracleSingleInstanceModel[]>>(`${getPath()}/list_instances/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new OracleSingleInstanceModel(item)),
  }));
}

/**
 * 查询主机列表
 */
export function getOracleSingleMachineList(params: {
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
  return http.get<ListBase<OracleSingleMachineModel[]>>(`${getPath()}/list_machines/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new OracleSingleMachineModel(item)),
  }));
}
