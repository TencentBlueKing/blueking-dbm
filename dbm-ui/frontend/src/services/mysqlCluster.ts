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

import RemotePairInstanceModel from '@services/model/mysql-cluster/remote-pair-instance';

import { useGlobalBizs } from '@stores';

import http from './http';
import type { MySQLClusterInfos } from './types/clusters';

export const findRelatedClustersByClusterIds = (params: { cluster_ids: number [] } & {bk_biz_id: number})
:Promise<Array<{
  cluster_id: number,
  cluster_info: MySQLClusterInfos,
  related_clusters: Array<MySQLClusterInfos>
 }>> => http.post(`/apis/mysql/bizs/${params.bk_biz_id}/cluster/find_related_clusters_by_cluster_ids/`, params);

export const findRelatedClustersByInstances = (params: {
  instances: Array<{
    bk_cloud_id: number,
    ip: string,
    bk_host_id: number,
    port: number,
  }>
} & {bk_biz_id: number}) => http.post(`/apis/mysql/bizs/${params.bk_biz_id}/cluster/find_related_clusters_by_instances/`, params);

export const getIntersectedSlaveMachinesFromClusters = (params: {
  bk_biz_id: number,
  cluster_ids: number[],
}): Promise<Array<{
  bk_biz_id: number,
  bk_cloud_id: number,
  bk_host_id: number,
  ip: string,
}>> => http.post(`/apis/mysql/bizs/${params.bk_biz_id}/cluster/get_intersected_slave_machines_from_clusters/`, params);

// 通过过滤条件批量查询集群
export const queryClusters = (params: {
  cluster_filters: Array<{
    id?: number,
    immute_domain?: string,
    cluster_type?: string,
    bk_biz_id?: number
  }>
} & {bk_biz_id: number}) => http.post<MySQLClusterInfos[]>(`/apis/mysql/bizs/${params.bk_biz_id}/cluster/query_clusters/`, params);

// 批量下载文件
export const batchFetchFile = (params: {
  file_path_list: string[]
}) => http.post<Array<{
  content: string,
  path: string,
  url: string
}>>('/apis/core/storage/batch_fetch_file_content/', params);

// 查询tendbcluster集群的remote_db/remote_dr
export const getRemoteParis = function (params: {
  cluster_ids: number[]
}) {
  const { currentBizId } = useGlobalBizs();
  return http.post<Array<{
    cluster_id: number,
    remote_pairs: {
      remote_db: RemotePairInstanceModel,
      remote_dr: RemotePairInstanceModel
    }[]
  }>>(`/apis/mysql/bizs/${currentBizId}/cluster/get_remote_pairs/`, params)
    .then(data => data.map(item => ({
      cluster_id: item.cluster_id,
      remote_pairs: item.remote_pairs.map(remotePair => ({
        remote_db: new RemotePairInstanceModel(remotePair.remote_db),
        remote_dr: new RemotePairInstanceModel(remotePair.remote_dr),
      })),
    })));
};

export const getRemoteMachineInstancePair = function (params: {
  instances?: string[],
  machines?: string[],
}) {
  const { currentBizId } = useGlobalBizs();
  return http.post<{
    instances: Record<string, RemotePairInstanceModel>,
    machines: Record<string, RemotePairInstanceModel>
  }>(`/apis/mysql/bizs/${currentBizId}/cluster/get_remote_machine_instance_pair/`, params);
};
