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

import RedisClusterNodeByIpModel from '@services/model/redis/redis-cluster-node-by-ip';

import http from '../http';
import type { InstanceInfos } from '../types/clusters';

/**
 * 判断 Mysql 实例是否存在
 */
export function checkMysqlInstances(params: Record<'instance_addresses', Array<string>> & { bizId: number }) {
  return http.post<Array<InstanceInfos>>(`/apis/mysql/bizs/${params.bizId}/instance/check_instances/`, params);
}

interface InstanceItem extends Omit<InstanceInfos, 'spec_config'> {
  spec_config: RedisClusterNodeByIpModel['spec_config'];
}

/**
 * 判断 Redis 实例是否存在
 */
export function checkRedisInstances(params: Record<'instance_addresses', Array<string>> & { bizId: number }) {
  return http.post<InstanceItem[]>(`/apis/redis/bizs/${params.bizId}/instance/check_instances/`, params);
}

/**
 * 判断 Mongo 实例是否存在
 */
export function checkMongoInstances(params: {
  bizId: number;
  instance_addresses: string[];
  cluster_ids?: number[],
}) {
  return http.post<InstanceItem[]>(`/apis/mongodb/bizs/${params.bizId}/instance/check_instances/`, params);
}
