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
import RedisClusterNodeByFilterModel from '@services/model/redis/redis-cluster-node-by-filter';
import RedisClusterNodeByIpModel from '@services/model/redis/redis-cluster-node-by-ip';
import RedisHostModel from '@services/model/redis/redis-host';

import { useGlobalBizs } from '@stores';

const { currentBizId } = useGlobalBizs();

// 根据IP查询集群、角色和规格
export const queryInfoByIp = (params: {
  ips: string[];
}) => http.post<RedisClusterNodeByIpModel[]>(`/apis/redis/bizs/${currentBizId}/toolbox/query_by_ip/`, params);

// 根据业务ID查询集群列表
export const listClusterList = () => http.get<RedisModel[]>(`/apis/redis/bizs/${currentBizId}/toolbox/query_cluster_list/`)
  .then(data => data.map(item => new RedisModel(item)));

// 根据cluster_id查询主从关系对
export const queryMasterSlavePairs = (params: {
  cluster_id: number;
}) => http.post<{
  master_ip: string;
  slave_ip: string
}[]>(`/apis/redis/bizs/${currentBizId}/toolbox/query_master_slave_pairs/`, params);


// 查询集群下的主机列表
export const queryClusterHostList = (params: {
  cluster_id?: number;
  ip?: string
}) => http.post<RedisHostModel[]>(`/apis/redis/bizs/${currentBizId}/toolbox/query_cluster_ips/`, params)
  .then(data => data.map(item => new RedisHostModel(item)));

// 批量过滤获取集群相关信息
export const queryInstancesByCluster = (params: {
  keywords: string[]
}) => http.post<RedisClusterNodeByFilterModel[]>(`/apis/redis/bizs/${currentBizId}/toolbox/query_instances_by_cluster/`, params);


export interface MasterSlaveByIp {
  cluster: {
    bk_cloud_id: number,
    cluster_type: string;
    deploy_plan_id: number,
    id: number,
    immute_domain: string;
    major_version: string;
    name: string;
    region: string;
  },
  instances: {
    bk_biz_id: number,
    bk_cloud_id: number,
    bk_host_id: number,
    bk_instance_id: number,
    instance: string;
    ip: string;
    name: string;
    phase: string;
    port: number,
    status: string;
  }[],
  master_ip: string;
  slave_ip: string;
}
// 根据masterIP查询集群、实例和slave
export const queryMasterSlaveByIp = (params: {
  ips: string[]
}) => http.post<MasterSlaveByIp[]>(`/apis/redis/bizs/${currentBizId}/toolbox/query_master_slave_by_ip/`, params);
