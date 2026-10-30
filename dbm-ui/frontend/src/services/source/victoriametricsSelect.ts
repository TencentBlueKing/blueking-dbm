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

import KubernetesComponentSpecModel from '@services/model/kubernetes/kubernetes-component-spec';
import KubernetesOperationLogModel from '@services/model/kubernetes/kubernetes-operation-log';
import VictoriametricsSelectModel from '@services/model/victoriametrics/victoriametrics-select';
import VictoriametricsSelectDetailModel from '@services/model/victoriametrics/victoriametrics-select-detail';
import VictoriametricsSelectInstanceModel from '@services/model/victoriametrics/victoriametrics-select-instance';

import http from '../http';
import type { ListBase, ResourceTopo } from '../types';

const getRootPath = () => `/apis/kubernetes/bizs/${window.PROJECT_CONFIG.BIZ_ID}/vmselect/vmselect_resources`;

export function getVictoriametricsSelectList(params: {
  bk_biz_id: number;
  cluster_ids?: string;
  creator?: string;
  domain?: string;
  id?: number;
  ip?: string;
  limit: number;
  name?: string;
  offset: number;
  type: string;
}) {
  return http.get<ListBase<VictoriametricsSelectModel[]>>(`${getRootPath()}/`, params).then((res) => ({
    ...res,
    results: res.results.map(
      (item) =>
        new VictoriametricsSelectModel(
          Object.assign(item, {
            permission: Object.assign({}, item.permission, res.permission),
          }),
        ),
    ),
  }));
}

/**
 * 获取集群详情
 */
export function getVictoriametricsSelectDetail(params: { id: number }) {
  return http
    .get<VictoriametricsSelectDetailModel>(`${getRootPath()}/${params.id}/`)
    .then((res) => new VictoriametricsSelectDetailModel(res));
}

/**
 * 获取集群实例列表
 */
export const getVictoriametricsSelectInstanceList = function (params: {
  cluster_name: string;
  k8s_cluster_name: string;
  namespace: string;
}) {
  return http
    .get<ListBase<VictoriametricsSelectInstanceModel[]>>(`${getRootPath()}/list_instances/`, params)
    .then((data) => ({
      ...data,
      results: data.results.map((item) => new VictoriametricsSelectInstanceModel(item)),
    }));
};

/**
 * 获取集群实例详情
 */
export const retrieveVictoriametricsSelectInstanceDetail = function (params: {
  cluster_id: number;
  clusterName: string;
  componentName: string;
  k8sClusterName: string;
  namespace: string;
  podName: string;
}) {
  return http
    .get<VictoriametricsSelectInstanceModel>(`${getRootPath()}/retrieve_instance/`, params)
    .then((res) => new VictoriametricsSelectInstanceModel(res));
};

/**
 * 修改集群元数据（别名 / 标签）
 */
export function updateVictoriametricsSelectClusterMeta(params: {
  bk_biz_id: number;
  cluster_alias?: string;
  cluster_id: number;
  tags?: Record<string, string>[];
}) {
  return http.post<Record<string, never>>(`${getRootPath()}/update_cluster_meta/`, params);
}

/**
 * 导出集群数据为 excel 文件
 */
export function exportVictoriametricsSelectClusterToExcel(params: { cluster_ids?: number[] }) {
  return http.post<string>(`${getRootPath()}/export_cluster/`, params, { responseType: 'blob' });
}

/**
 * 导出实例数据为 excel 文件
 */
export function exportVictoriametricsSelectInstanceToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${getRootPath()}/export_instance/`, params, { responseType: 'blob' });
}

/**
 * 获取集群拓扑
 */
export function getVictoriametricsSelectTopoGraph(params: {
  cluster_id: number;
  k8sClusterName: string;
  namespace: string;
}) {
  return http.get<ResourceTopo>(`${getRootPath()}/${params.cluster_id}/get_topo_graph/`, params);
}

/**
 * 获取集群操作日志接口
 */
export const getVictoriametricsSelectOperationLog = function (params: {
  bk_biz_id: number;
  clusterName: string;
  creator?: string;
  endTime?: string;
  k8sClusterName: string;
  limit: number;
  namespace: string;
  offset: number;
  requestParams?: string;
  requestType?: string;
  startTime?: string;
}) {
  return http
    .get<ListBase<KubernetesOperationLogModel[]>>(`${getRootPath()}/get_operation_log/`, params)
    .then((data) => ({
      ...data,
      results: data.results.map((item) => new KubernetesOperationLogModel(item)),
    }));
};

/**
 * 获取集群组件规格
 */
export const getVictoriametricsSelectComponentSpec = function (params: {
  clusterName: string;
  k8sClusterName: string;
  namespace: string;
}) {
  return http
    .get<KubernetesComponentSpecModel>(`${getRootPath()}/get_component_spec/`, params)
    .then((res) => new KubernetesComponentSpecModel(res));
};
