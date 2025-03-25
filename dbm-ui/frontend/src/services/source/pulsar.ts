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

import PulsarModel from '@services/model/pulsar/pulsar';
import PulsarDetailModel from '@services/model/pulsar/pulsar-detail';
import PulsarInstanceModel from '@services/model/pulsar/pulsar-instance';
import PulsarMachineModel from '@services/model/pulsar/pulsar-machine';
import PulsarNodeModel from '@services/model/pulsar/pulsar-node';
import type { BigDataClusterPassword, ListBase } from '@services/types';

import http from '../http';

const getRootPath = () => `/apis/bigdata/bizs/${window.PROJECT_CONFIG.BIZ_ID}/pulsar/pulsar_resources`;

/**
 * 获取集群列表
 */
export function getPulsarList(params: { bk_biz_id: number } & Record<string, any>) {
  return http.get<ListBase<PulsarModel[]>>(`${getRootPath()}/`, params).then((data) => ({
    ...data,
    results: data.results.map(
      (item) =>
        new PulsarModel(
          Object.assign(item, {
            permission: Object.assign({}, item.permission, data.permission),
          }),
        ),
    ),
  }));
}

/**
 * 获取查询返回字段
 */
export function getPulsarTableFields() {
  return http.get<ListBase<PulsarModel[]>>(`${getRootPath()}/get_table_fields/`);
}

/**
 * 获取实例列表
 */
export function getPulsarInstanceList(params: { bk_biz_id: number } & Record<string, any>) {
  return http.get<ListBase<PulsarInstanceModel[]>>(`${getRootPath()}/list_instances/`, params).then((data) => ({
    ...data,
    results: data.results.map((item: PulsarInstanceModel) => new PulsarInstanceModel(item)),
  }));
}

/**
 *  获取实例详情
 */
export function retrievePulsarInstance(params: { bk_biz_id: number }) {
  return http.get<ListBase<PulsarModel[]>>(`${getRootPath()}/retrieve_instance/`, params);
}

/**
 * 获取集群详情
 */
export function getPulsarDetail(params: { id: number }) {
  return http.get<PulsarDetailModel>(`${getRootPath()}/${params.id}/`).then((data) => new PulsarDetailModel(data));
}

/**
 * 获取集群拓扑
 */
export function getPulsarTopoGraph(params: { cluster_id: number }) {
  return http.get<ListBase<PulsarModel[]>>(`${getRootPath()}/${params.cluster_id}/get_topo_graph/`);
}

/**
 * 获取 Pulsar 集群访问密码
 */
export function getPulsarPassword(params: { cluster_id: number }) {
  return http.get<BigDataClusterPassword>(`${getRootPath()}/${params.cluster_id}/get_password/`);
}

/**
 * 获取 Pulsar 集群节点列表信息
 */
export function getPulsarNodeList(
  params: {
    bk_biz_id: number;
    cluster_id: number;
  } & Record<string, any>,
) {
  return http
    .get<ListBase<Array<PulsarNodeModel>>>(`${getRootPath()}/${params.cluster_id}/list_nodes/`, params)
    .then((data) => ({
      ...data,
      results: data.results.map(
        (item) =>
          new PulsarNodeModel(
            Object.assign(item, {
              permission: data.permission,
            }),
          ),
      ),
    }));
}

/**
 * 导出集群数据为 excel 文件
 */
export function exportPulsarClusterToExcel(params: { cluster_ids?: number[] }) {
  return http.post<string>(`${getRootPath()}/export_cluster/`, params, { responseType: 'blob' });
}

/**
 * 导出实例数据为 excel 文件
 */
export function exportPulsarInstanceToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${getRootPath()}/export_instance/`, params, { responseType: 'blob' });
}

/**
 * 查询主机列表
 */
export function getPulsarMachineList(params: {
  add_role_count?: boolean;
  bk_agent_id?: string;
  bk_city_name?: string;
  bk_cloud_id?: number;
  bk_host_id?: number;
  bk_os_name?: string;
  cluster_ids?: string;
  cluster_type?: string;
  creator?: string;
  instance_role?: string;
  ip?: string;
  limit?: number;
  machine_type?: string;
  offset?: number;
}) {
  return http.get<ListBase<PulsarMachineModel[]>>(`${getRootPath()}/list_machines/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new PulsarMachineModel(item)),
  }));
}
