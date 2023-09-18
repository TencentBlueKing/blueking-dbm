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
import RedisClusterNodeByIpModel from '@services/model/redis/redis-cluster-node-by-ip';
import RedisDSTHistoryJobModel from '@services/model/redis/redis-dst-history-job';
import RedisDSTJobTaskModel from '@services/model/redis/redis-dst-job-task';
import RedisHostModel from '@services/model/redis/redis-host';
import RedisRollbackModel from '@services/model/redis/redis-rollback';

import { useGlobalBizs } from '@stores';

import type { InstanceInfos } from '../types/clusters';
import type { ListBase } from '../types/common';


// 根据IP查询集群、角色和规格
export const queryInfoByIp = (params: {
  ips: string[];
}) => {
  const { currentBizId } = useGlobalBizs();
  return http.post<RedisClusterNodeByIpModel[]>(`/apis/redis/bizs/${currentBizId}/toolbox/query_by_ip/`, params)
    .then(data => data.map(item => new RedisClusterNodeByIpModel(item)));
};

// 根据cluster_id查询主从关系对
export const queryMasterSlavePairs = (params: {
  cluster_id: number;
}) => {
  const { currentBizId } = useGlobalBizs();
  return http.post<{
    master_ip: string;
    slave_ip: string
  }[]>(`/apis/redis/bizs/${currentBizId}/toolbox/query_master_slave_pairs/`, params);
};

// 查询集群下的主机列表
export const queryClusterHostList = (params: {
  cluster_id?: number;
  ip?: string;
}) => {
  const { currentBizId } = useGlobalBizs();
  return http.post<RedisHostModel[]>(`/apis/redis/bizs/${currentBizId}/toolbox/query_cluster_ips/`, params)
    .then(data => data.map(item => new RedisHostModel(item)));
};

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
}) => {
  const { currentBizId } = useGlobalBizs();
  return http.post<MasterSlaveByIp[]>(`/apis/redis/bizs/${currentBizId}/toolbox/query_master_slave_by_ip/`, params);
};

// 获取集群列表
export const listClusterList = (bizId: number, params?: {
  domain: string
}) => http.get<ListBase<RedisModel[]>>(`/apis/redis/bizs/${bizId}/redis_resources/`, params).then(data => data.results.map(item => new RedisModel(item)));

export interface InstanceItem extends Omit<InstanceInfos, 'spec_config'> {
  spec_config: RedisClusterNodeByIpModel['spec_config']
}

/**
 * 判断实例是否存在
 */
export const checkInstances = (
  bizId: number,
  params: Record<'instance_addresses', Array<string>>,
) => http.post<InstanceItem[]>(`/apis/redis/bizs/${bizId}/instance/check_instances/`, params);

// 构造实例列表
export const getRollbackList = (params?: {
  limit: number;
  offset: number;
  temp_cluster_proxy?: string; // ip:port
}) => {
  const { currentBizId } = useGlobalBizs();
  return http.get<ListBase<RedisRollbackModel[]>>(`/apis/redis/bizs/${currentBizId}/rollback/`, params)
    .then(res => ({
      ...res,
      results: res.results.map(item => new RedisRollbackModel(item)),
    }));
};


// 获取DTS历史任务以及其对应task cnt
export const getRedisDTSHistoryJobs = (params: {
  start_time?: string,
  end_time?: string,
  cluster_name?: string,
  page?: number,
  page_size?: number,
}) => {
  const { currentBizId } = useGlobalBizs();
  return http.post<{ total_cnt: number, jobs: RedisDSTHistoryJobModel[] }>(`/apis/redis/bizs/${currentBizId}/dts/history_jobs/`, params);
};

// 获取迁移任务task列表,失败的排在前面
export const getRedisDTSJobTasks = (params: {
  bill_id: number,
  src_cluster: string,
  dst_cluster: string,
}) => {
  const { currentBizId } = useGlobalBizs();
  return http.post<RedisDSTJobTaskModel[]>(`/apis/redis/bizs/${currentBizId}/dts/job_tasks/`, params).then(arr => arr.map(item => new RedisDSTJobTaskModel(item)));
};

// dts job批量断开同步
export const setJobDisconnectSync = (params: {
  bill_id: number,
  src_cluster: string,
  dst_cluster: string,
}) => {
  const { currentBizId } = useGlobalBizs();
  return http.post<unknown>(`/apis/redis/bizs/${currentBizId}/dts/job_disconnect_sync/`, params);
};


// dts job 批量失败重试
export const setJobTaskFailedRetry = (params: {
  task_ids: number[]
}) => {
  const { currentBizId } = useGlobalBizs();
  return http.post<number[]>(`/apis/redis/bizs/${currentBizId}/dts/job_task_failed_retry/`, params);
};

// dts 外部redis连接行测试
export const testRedisConnection = (params: {
  data_copy_type: string,
  infos: {
    src_cluster: string,
    src_cluster_password: string,
    dst_cluster: string,
    dst_cluster_password: string,
  }[]
}) => {
  const { currentBizId } = useGlobalBizs();
  return http.post<boolean>(`/apis/redis/bizs/${currentBizId}/dts/test_redis_connection/`, params);
};
