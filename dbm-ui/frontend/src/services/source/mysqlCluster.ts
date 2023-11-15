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

import http from '../http';
import type {
  MySQLClusterInfos,
  ResourceItem,
} from '../types/clusters';

const { currentBizId } = useGlobalBizs();

const path = `/apis/mysql/bizs/${currentBizId}/cluster`;

/**
 * 通过集群查询同机关联集群
 */
export const findRelatedClustersByClusterIds = function (params: {
  cluster_ids: number []
  bk_biz_id: number
}) {
  return http.post<Array<{
    cluster_id: number,
    cluster_info: MySQLClusterInfos,
    related_clusters: Array<MySQLClusterInfos>
  }>>(`${path}/find_related_clusters_by_cluster_ids/`, params);
};

/**
 * 通过实例查询同机关联集群
 */
export const findRelatedClustersByInstances = function (params: {
  instances: Array<{
    bk_cloud_id: number,
    ip: string,
    bk_host_id: number,
    port: number,
  }>
  bk_biz_id: number
}) {
  return http.post(`${path}/find_related_clusters_by_instances/`, params);
};

/**
 * 获取关联集群从库的交集
 */
export const getIntersectedSlaveMachinesFromClusters = function (params: {
  bk_biz_id: number,
  cluster_ids: number[],
}) {
  return http.post<Array<{
    bk_biz_id: number,
    bk_cloud_id: number,
    bk_host_id: number,
    ip: string,
  }>>(`${path}/get_intersected_slave_machines_from_clusters/`, params);
};

/**
 * [tendbcluster]根据实例/机器查询关联对
 */
export const getRemoteMachineInstancePair = function (params: {
  instances?: string[],
  machines?: string[],
}) {
  return http.post<{
    instances: Record<string, RemotePairInstanceModel>,
    machines: Record<string, RemotePairInstanceModel>
  }>(`${path}/get_remote_machine_instance_pair/`, params);
};

/**
 * 查询tendbcluster集群的remote_db/remote_dr
 */
export const getRemoteParis = function (params: {
  cluster_ids: number[]
}) {
  return http.post<Array<{
    cluster_id: number,
    remote_pairs: {
      remote_db: RemotePairInstanceModel,
      remote_dr: RemotePairInstanceModel
    }[]
  }>>(`${path}/get_remote_pairs/`, params).then(data => data.map(item => ({
    cluster_id: item.cluster_id,
    remote_pairs: item.remote_pairs.map(remotePair => ({
      remote_db: new RemotePairInstanceModel(remotePair.remote_db),
      remote_dr: new RemotePairInstanceModel(remotePair.remote_dr),
    })),
  })));
};

/**
 * 通过过滤条件批量查询集群
 */
export const queryClusters = function (params: {
  cluster_filters: Array<{
    id?: number,
    immute_domain?: string,
    cluster_type?: string,
    bk_biz_id?: number
  }>
  bk_biz_id: number
}) {
  return http.post<MySQLClusterInfos[]>(`${path}/query_clusters/`, params);
};

/**
 * 通过集群域名获取集群详情
 */
export const getClusterInfoByDomains = function (params: Record<'cluster_filters', Array<{ immute_domain: string }>> & { bizId: number }) {
  return http.post<ResourceItem[]>(`${path}/query_clusters/`, params);
};
