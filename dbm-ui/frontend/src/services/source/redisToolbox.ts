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
import http from '@services/http';
import RedisModel from '@services/model/redis/redis';

import type { ListBase } from '../types';

const getRootPath = () => `/apis/redis/bizs/${window.PROJECT_CONFIG.BIZ_ID}/toolbox`;

interface MachineInstancePairItem {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_host_id: number;
  bk_instance_id: number;
  instance: string;
  ip: string;
  name: string;
  phase: string;
  port: number;
  status: string;
}

/**
 * 根据cluster_id查询主从关系对
 */
export function queryMasterSlavePairs(params: { cluster_id: number }) {
  return http.post<
    {
      master_ip: string;
      masters: MachineInstancePairItem;
      slave_ip: string;
      slaves: MachineInstancePairItem;
    }[]
  >(`${getRootPath()}/query_master_slave_pairs/`, params);
}

// 获取集群列表(重建从库)
export const listClustersCreateSlaveProxy = async (params: { bk_biz_id: number }) =>
  http
    .get<ListBase<RedisModel[]>>(`/apis/redis/bizs/${params.bk_biz_id}/redis_resources/`, params)
    .then((data) =>
      data.results
        .map((item) => new RedisModel(item))
        .filter((item) => item.redis_slave.filter((slave) => slave.status !== 'running').length > 0),
    );

/**
 * 查询集群版本信息
 */
export function getClusterVersions(params: {
  node_type: string;
  type: string;
  cluster_id?: number;
  cluster_type?: string;
}) {
  return http.get<string[]>(`${getRootPath()}/get_cluster_versions/`, params);
}

/**
 * 根据IP/实例查询关联对
 */
export function queryMachineInstancePair(params: {
  machines?: string[]; // 0:127.0.0.1 云区域ID:IP
  instances?: string[]; // IP:PORT
}) {
  return http.post<{
    machines?: Record<
      string,
      MachineInstancePairItem & {
        related_instances: MachineInstancePairItem[];
        related_pair_instances: MachineInstancePairItem[];
        related_clusters: {
          bk_biz_id: number;
          bk_cloud_id: number;
          cluster_type: string;
          id: number;
          immute_domain: string;
          major_version: string;
          name: string;
          region: string;
        }[];
      }
    >;
    instances?: Record<string, MachineInstancePairItem>;
  }>(`${getRootPath()}/query_machine_instance_pair/`, params);
}

/**
 * 通过集群查询同机关联集群
 */
export function findRelatedClustersByClusterIds(params: { cluster_ids: number[] }) {
  return http.post<
    Array<{
      cluster_id: number;
      cluster_info: RedisModel;
      related_clusters: Array<RedisModel>;
    }>
  >(`${getRootPath()}/find_related_clusters_by_cluster_ids/`, params);
}

/**
 * 通过集群查询同机关联集群
 */
export function getRedisClusterCapacityUpdateInfo(params: {
  cluster_id: number;
  new_storage_version: string;
  new_spec_id: number;
  new_machine_group_num: number;
  new_shards_num: number;
}) {
  return http.get<{
    capacity_update_type: string; // 原地变更(keep_current_machines)、替换变更(all_machines_replace)
    require_spec_id: number;
    require_machine_group_num: number;
    err_msg: string;
  }>(`${getRootPath()}/get_cluster_capacity_update_info/`, params);
}
