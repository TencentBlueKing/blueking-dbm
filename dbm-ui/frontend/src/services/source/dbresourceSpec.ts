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

import http from '../http';
import RedisClusterSpecModel from '../model/resource-spec/redis-cluster-sepc';
import ResourceSpecModel from '../model/resource-spec/resourceSpec';
import type { ListBase } from '../types';

const path = '/apis/dbresource/spec';

/**
 * 获取资源规格列表
 */
export const getResourceSpecList = function (params: Record<string, any> & {
  spec_cluster_type: string,
  spec_machine_type?: string,
}) {
  return http.get<ListBase<ResourceSpecModel[]>>(`${path}/`, params).then(res => ({
    ...res,
    results: res.results.map((item: ResourceSpecModel) => new ResourceSpecModel(item)),
  }));
};

/**
 * 新建规格
 */
export const createResourceSpec = function (params: Record<any, any>) {
  return http.post<ResourceSpecModel>(`${path}/`, params);
};

/**
 * 批量删除规格
 */
export const batchDeleteResourceSpec = function (params: Record<string, any> & { spec_ids: number[] }) {
  return http.delete(`${path}/batch_delete/`, params, {});
};

/**
 * 筛选集群部署规格方案
 */
export const getFilterClusterSpec = function (params: {
  spec_cluster_type: string,
  spec_machine_type: string,
  capacity: number,
  future_capacity: number,
  qps?: {
    min: number,
    max: number
  },
  shard_num?: number,
}) {
  return http.post<RedisClusterSpecModel[]>(`${path}/filter_cluster_spec/`, params);
};

/**
 * 获取 qps 的范围
 */
export const queryQPSRange = function (params: {
  spec_cluster_type: string,
  spec_machine_type: string,
  capacity: number,
  future_capacity: number,
}) {
  return http.get<{
    max: number,
    min: number
  }>(`${path}/query_qps_range/`, params);
};

/**
 * 获取推荐规格
 */
export const fetchRecommendSpec = function (params: {
  cluster_id: number,
  role: string,
} | {
  instance_id: number,
  role: string,
}) {
  return http.get<ResourceSpecModel[]>(`${path}/recommend_spec/`, params).then(data => data.map(item => new ResourceSpecModel(item)));
};

/**
 * 校验规格名称是否重复
 */
export const verifyDuplicatedSpecName = function (params: {
  spec_cluster_type: string,
  spec_machine_type: string,
  spec_name: string,
  spec_id?: number
}) {
  return http.post<boolean>(`${path}/verify_duplicated_spec_name/`, params);
};

/**
 * 规格详情
 */
export const getResourceSpec = function (params: { spec_id: number }) {
  return http.get<ResourceSpecModel>(`${path}/${params.spec_id}/`);
};

/**
 * 更新规格
 */
export const updateResourceSpec = function (params: Record<string, any> & { specId: number }) {
  return http.put<ResourceSpecModel>(`${path}/${params.specId}/`, params);
};

/**
 * 删除规格
 */
export const deleteResourceSpec = function (params: { specId: number }) {
  return http.delete(`${path}/${params.specId}/`);
};
