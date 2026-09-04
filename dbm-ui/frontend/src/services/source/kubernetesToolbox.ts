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

const getRootPath = () => `/apis/kubernetes/toolbox`;

import http from '../http';

/**
 * 获取存储版本信息
 */
export function getAddonVersions(params: { addonType: 'surrealdb' | 'qdrant' | 'victoriametrics' }) {
  return http.get<
    {
      addonVersion: string;
      supportedVersions: string[];
    }[]
  >(`${getRootPath()}/get_addon_versions/`, params);
}

/**
 * 查询城市信息
 */
export function getRegions() {
  return http.get<
    {
      k8sClusterList: {
        clusterAlias: string;
        clusterName: string;
        vpcID: string;
      }[];
      provider: string;
      regionCode: string;
      regionName: string;
    }[]
  >(`${getRootPath()}/get_regions/`);
}

/**
 * 查询BCS集群信息
 */
export function getBcsClusters(params: { isPublic: boolean }) {
  return http.get<
    {
      k8sClusterList: {
        clusterAlias: string;
        clusterName: string;
        vpcID: string;
      }[];
      provider: string;
      regionCode: string;
      regionName: string;
    }[]
  >(`${getRootPath()}/get_k8s_cluster_config/`, params);
}

/**
 * 查询集群部署套餐
 */
export function getAddonSpecPlan(params: {
  addonType: 'surrealdb' | 'qdrant' | 'victoriametrics';
  addonVersion: string;
}) {
  return http.get<
    {
      addonName: string;
      addonType: string;
      addonVersion: string;
      components: {
        componentName: string;
        cpuCores: number;
        diskSizeGb: number;
        id: number;
        memoryGb: number;
      }[];
      dbmClusterType: string;
      id: number;
      specLevel: string;
      specLevelAlias: string;
    }[]
  >(`${getRootPath()}/get_addon_spec_plan/`, params);
}

/**
 * 获取组件配置
 */
export function getComponentConfig(params: {
  bk_username: string;
  clusterName: string;
  componentName: string;
  k8sClusterName: string;
  namespace: string;
}) {
  return http.get<{
    clusterName: string;
    componentName: string;
    config: Record<string, string>;
    namespace: string;
    storageAddonType: string;
  }>(`${getRootPath()}/component_config/`, params);
}

/**
 * 重启组件
 */
export function restartComponent(params: {
  bk_username: string;
  clusterName: string;
  k8sClusterName: string;
  namespace: string;
  restart: {
    componentName: string;
  }[];
}) {
  return http.post(`${getRootPath()}/restart_component/`, params);
}

/**
 * 组件水平扩缩容
 */
export function hscalingComponent(params: {
  bk_username: string;
  clusterName: string;
  horizontalScaling: { componentName: string; scaleOut: { replicaChanges: number } }[];
  k8sClusterName: string;
  namespace: string;
}) {
  return http.post(`${getRootPath()}/hscaling_component/`, params);
}

/**
 * 组件垂直扩容
 */
export function vscalingComponent(params: {
  bk_username: string;
  clusterName: string;
  componentList: {
    componentName: string;
    limit: { cpu: number; memory: string };
    request: { cpu: number; memory: string };
  }[];
  k8sClusterName: string;
  namespace: string;
}) {
  return http.post(`${getRootPath()}/vscaling_component/`, params);
}

/**
 * 磁盘扩容
 */
export function vexpansionComponent(params: {
  bk_username: string;
  clusterName: string;
  componentList: {
    componentName: string;
    storage: string; // 单位Gi
  }[];
  k8sClusterName: string;
  namespace: string;
}) {
  return http.post(`${getRootPath()}/vexpansion_component/`, params);
}

/**
 * 组件pod删除
 */
export function deleteComponent(params: {
  bk_username: string;
  clusterName: string;
  k8sClusterName: string;
  namespace: string;
  podName: string;
}) {
  return http.post(`${getRootPath()}/delete_component/`, params);
}

/**
 * 修改组件配置
 */
export function patchComponentConfig(params: {
  bk_username: string;
  clusterName: string;
  componentList: {
    componentName: string;
    config: ServiceReturnType<typeof getComponentConfig>['config'];
  }[];
  k8sClusterName: string;
  namespace: string;
}) {
  return http.post(`${getRootPath()}/patch_component_config/`, params);
}

/**
 * 获取组件日志
 */
export function getPodLog(params: {
  bk_username: string;
  clusterName: string;
  componentName: string;
  container: string;
  // endTime?: string;
  k8sClusterName: string;
  limit: number;
  namespace: string;
  offset: number;
  podName: string;
  // search_key?: string;
  // startTime?: string;
}) {
  return http.get(`${getRootPath()}/pod_log/`, params).then(
    (data: {
      count: number;
      result: {
        message: string; // json字符串
        timestamp: string;
      }[];
    }) => ({
      ...data,
      results: data.result,
    }),
  );
}
