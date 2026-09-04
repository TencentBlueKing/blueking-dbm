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
import VictoriametricsInstanceModel from '@services/model/victoriametrics/victoriametrics-instance';
import VictoriametricsStandardModel from '@services/model/victoriametrics/victoriametrics-standard';
import VictoriametricsStandardDetailModel from '@services/model/victoriametrics/victoriametrics-standard-detail';

import http from '../http';
import type { ListBase, ResourceTopo } from '../types';

const getRootPath = () => `/apis/kubernetes/bizs/${window.PROJECT_CONFIG.BIZ_ID}/vmcluster/vmcluster_resources`;

export function getVictoriametricsStandardList(params: {
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
  return http.get<ListBase<VictoriametricsStandardModel[]>>(`${getRootPath()}/`, params).then((res) => ({
    ...res,
    results: res.results.map(
      (item) =>
        new VictoriametricsStandardModel(
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
export function getVictoriametricsStandardDetail(params: { id: number }) {
  return http
    .get<VictoriametricsStandardDetailModel>(`${getRootPath()}/${params.id}/`)
    .then((res) => new VictoriametricsStandardDetailModel(res));
}

/**
 * 获取集群实例列表
 */
export const getVictoriametricsStandardInstanceList = function (params: {
  cluster_name: string;
  k8s_cluster_name: string;
  namespace: string;
}) {
  return http
    .get<ListBase<VictoriametricsInstanceModel[]>>(`${getRootPath()}/list_instances/`, params)
    .then((data) => ({
      ...data,
      results: data.results.map((item) => new VictoriametricsInstanceModel(item)),
    }));
};

/**
 * 获取集群实例详情
 */
export const retrieveVictoriametricsStandardInstanceDetail = function (params: {
  cluster_id: number;
  clusterName: string;
  componentName: string;
  k8sClusterName: string;
  namespace: string;
  podName: string;
}) {
  return http
    .get<VictoriametricsInstanceModel>(`${getRootPath()}/retrieve_instance/`, params)
    .then((res) => new VictoriametricsInstanceModel(res));
};

/**
 * 修改集群元数据（别名 / 标签）
 */
export function updateVictoriametricsStandardClusterMeta(params: {
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
export function exportVictoriametricsStandardClusterToExcel(params: { cluster_ids?: number[] }) {
  return http.post<string>(`${getRootPath()}/export_cluster/`, params, { responseType: 'blob' });
}

/**
 * 导出实例数据为 excel 文件
 */
export function exportVictoriametricsStandardInstanceToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${getRootPath()}/export_instance/`, params, { responseType: 'blob' });
}

/**
 * 获取集群拓扑
 */
export function getVictoriametricsStandardTopoGraph(params: {
  cluster_id: number;
  k8sClusterName: string;
  namespace: string;
}) {
  return http.get<ResourceTopo>(`${getRootPath()}/${params.cluster_id}/get_topo_graph/`, params);
}

/**
 * 获取集群操作日志接口
 */
export const getVictoriametricsStandardOperationLog = function (params: {
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
export const getVictoriametricsStandardComponentSpec = function (params: {
  clusterName: string;
  k8sClusterName: string;
  namespace: string;
}) {
  return http
    .get<KubernetesComponentSpecModel>(`${getRootPath()}/get_component_spec/`, params)
    .then((res) => new KubernetesComponentSpecModel(res));
};

/**
 * 存储入口 CLB 启用 / 停用
 * TODO: 后端接口契约就绪后替换路径与入参（当前为占位）
 */
export function toggleVictoriametricsStorageClb(params: { cluster_id: number; enable: boolean }) {
  return http.post<Record<string, never>>(
    `${getRootPath()}/toggle_storage_clb/`,
    {
      cluster_id: params.cluster_id,
      enable: params.enable,
    },
    // TODO: 停用弹窗确认后调用，成功后写入操作记录（待后端通道确认）
  );
}
