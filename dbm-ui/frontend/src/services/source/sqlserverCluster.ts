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

import SqlServerHaCluster from '@services/model/sqlserver/sqlserver-ha';

import http from '../http';

const getRootPath = (bizId = window.PROJECT_CONFIG.BIZ_ID) => `/apis/sqlserver/bizs/${bizId}/cluster`;

/**
 * 通过集群查询同机关联集群
 */
export function findRelatedClustersByClusterIds(params: { bk_biz_id: number; cluster_ids: number[]; role?: string }) {
  return http.post<
    Array<{
      cluster_id: number;
      cluster_info: SqlServerHaCluster;
      related_clusters: Array<SqlServerHaCluster>;
    }>
  >(`${getRootPath()}/find_related_clusters_by_cluster_ids/`, params);
}

/**
 * 通过实例查询同机关联集群
 */
export function findRelatedClustersByInstances(params: {
  bk_biz_id: number;
  instances: Array<{
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
    port: number;
  }>;
}) {
  return http.post(`${getRootPath()}/find_related_clusters_by_instances/`, params);
}

/**
 * 获取关联集群从库的交集
 */
export function getIntersectedSlaveMachinesFromClusters(params: {
  bk_biz_id: number;
  cluster_ids: number[];
  is_stand_by?: boolean;
}) {
  return http.post<
    Array<{
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }>
  >(`${getRootPath(params.bk_biz_id)}/get_intersected_slave_machines_from_clusters/`, params);
}
