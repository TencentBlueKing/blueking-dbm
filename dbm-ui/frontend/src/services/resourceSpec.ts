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

import http from './http';
import ResourceSpecModel from './model/resource-spec/resourceSpec';
import type { ListBase } from './types/common';

export interface FilterClusterSpecItem {
  creator: string,
  updater: string,
  spec_id: number,
  spec_name: string,
  spec_cluster_type: string,
  spec_machine_type: string,
  cpu: {
    max: number,
    min: number
  },
  mem: {
    max: number,
    min: number
  },
  device_class: string[],
  storage_spec: {
    size: number,
    type: string,
    mount_point: string
  }[],
  desc: string,
  instance_num: number,
  qps: {
    max: number,
    min: number
  },
  cluster_qps: string,
  capacity: number,
  machine_pair: number,
  cluster_capacity: number,
  cluster_shard_num: number
}

// 获取资源规格列表
export const getResourceSpecList = function (params: Record<string, any> & {
  spec_cluster_type: string,
  spec_machine_type?: string,
}) {
  return http.get<ListBase<ResourceSpecModel[]>>('/apis/dbresource/spec/', params)
    .then(res => ({
      ...res,
      results: res.results.map((item: ResourceSpecModel) => new ResourceSpecModel(item)),
    }));
};

// 新建规格
export const createResourceSpec = function (params: Record<any, any>): Promise<ResourceSpecModel> {
  return http.post('/apis/dbresource/spec/', params);
};

// 更新规格
export const updateResourceSpec = function (specId: number, params: Record<string, any>): Promise<ResourceSpecModel> {
  return http.put(`/apis/dbresource/spec/${specId}/`, params);
};

// 批量删除规格
export const batchDeleteResourceSpec = function (params: Record<string, any> & { spec_ids: number[] }) {
  return http.delete('/apis/dbresource/spec/batch_delete/', params, {});
};

// 删除规格
export const deleteResourceSpec = function (specId: number) {
  return http.delete(`/apis/dbresource/spec/${specId}/`);
};

// 获取 qps 的范围
export const queryQPSRange = (params: {
  spec_cluster_type: string,
  spec_machine_type: string,
  capacity: number,
  future_capacity: number,
}) => http.get<{ max: number, min: number }>('/apis/dbresource/spec/query_qps_range/', params);

// 筛选集群部署规格方案
export const getFilterClusterSpec = (params: {
  spec_cluster_type: string,
  spec_machine_type: string,
  shard_num: number,
  capacity: number,
  future_capacity: number,
  qps: {
    min: number,
    max: number
  }
}) => http.post<FilterClusterSpecItem[]>('/apis/dbresource/spec/filter_cluster_spec/', params);
