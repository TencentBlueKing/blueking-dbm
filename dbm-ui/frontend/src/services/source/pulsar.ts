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
import PulsarInstanceModel from '@services/model/pulsar/pulsar-instance';
import PulsarNodeModel from '@services/model/pulsar/pulsar-node';
import PulsarPasswordModel from '@services/model/pulsar/pulsar-password';

import { useGlobalBizs } from '@stores';

import http from '../http';
import type { ListBase } from '../types';

const { currentBizId } = useGlobalBizs();

const path = `/apis/bigdata/bizs/${currentBizId}/pulsar/pulsar_resources`;

/**
 * 获取集群列表
 */
export function getPulsarList(params: Record<string, any> & { bk_biz_id: number }) {
  return http.get<ListBase<PulsarModel[]>>(`${path}/`, params)
    .then(data => ({
      ...data,
      results: data.results.map(item => new PulsarModel(Object.assign(item, {
        permission: Object.assign(item.permission, data.permission),
      }))),
    }));
}

/**
 * 获取查询返回字段
 */
export function getPulsarTableFields() {
  return http.get<ListBase<PulsarModel[]>>(`${path}/get_table_fields/`);
}

/**
 * 获取实例列表
 */
export function getPulsarInstanceList(params: Record<string, any> & { bk_biz_id: number }) {
  return http.get<ListBase<PulsarInstanceModel[]>>(`${path}/list_instances/`, params)
    .then(data => ({
      ...data,
      results: data.results.map((item: PulsarInstanceModel) => new PulsarInstanceModel(item)),
    }));
}

/**
 *  获取实例详情
 */
export function retrievePulsarInstance(params: { bk_biz_id: number }) {
  return http.get<ListBase<PulsarModel[]>>(`${path}/retrieve_instance/`, params);
}

/**
 * 获取集群详情
 */
export function getPulsarDetail(params: { id: number }) {
  return http.get<PulsarModel>(`${path}/${params.id}/`)
    .then(data => new PulsarModel(data));
}

/**
 * 获取集群拓扑
 */
export function getPulsarTopoGraph(params: { cluster_id: number }) {
  return http.get<ListBase<PulsarModel[]>>(`${path}/${params.cluster_id}/get_topo_graph/`);
}

/**
 * 获取 Pulsar 集群访问密码
 */
export function getPulsarPassword(params: { cluster_id: number }) {
  return http.get<PulsarPasswordModel>(`${path}/${params.cluster_id}/get_password/`)
    .then(data => new PulsarPasswordModel(data));
}

/**
 * 获取 Pulsar 集群节点列表信息
 */
export function getPulsarNodeList(params: Record<string, any> & {
  bk_biz_id: number,
  cluster_id: number
}) {
  return http.get<ListBase<Array<PulsarNodeModel>>>(`${path}/${params.cluster_id}/list_nodes/`, params)
    .then(data => ({
      ...data,
      results: data.results.map(item => new PulsarNodeModel(Object.assign(item, {
        permission: data.permission,
      }))),
    }));
}

/**
 * 导出集群数据为 excel 文件
 */
export function exportPulsarClusterToExcel(params: { cluster_ids?: number[] }) {
  return http.post<string>(`${path}/export_cluster/`, params);
}

/**
 * 导出实例数据为 excel 文件
 */
export function exportPulsarInstanceToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${path}/export_instance/`, params);
}

