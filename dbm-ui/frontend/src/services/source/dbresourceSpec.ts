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
import ClusterSpecModel from '../model/resource-spec/cluster-sepc';
import ResourceSpecModel from '../model/resource-spec/resourceSpec';
import type { ListBase } from '../types';

const path = '/apis/dbresource/spec';

/**
 * 获取资源规格列表
 */
export function getResourceSpecList(
  params: Record<string, any> & {
    spec_cluster_type: string;
    spec_machine_type?: string;
    enable?: boolean;
  },
) {
  return http.get<ListBase<ResourceSpecModel[]>>(`${path}/`, params).then((data) => ({
    ...data,
    results: data.results.map(
      (item) =>
        new ResourceSpecModel(
          Object.assign(item, {
            permission: Object.assign({}, item.permission, data.permission),
          }),
        ),
    ),
  }));
}

/**
 * 新建规格
 */
export function createResourceSpec(params: Record<any, any>) {
  return http.post<ResourceSpecModel>(`${path}/`, params);
}

/**
 * 批量删除规格
 */
export function batchDeleteResourceSpec(params: Record<string, any> & { spec_ids: number[] }) {
  return http.delete(`${path}/batch_delete/`, params, {});
}

/**
 * 筛选集群部署规格方案
 */
export function getFilterClusterSpec(params: {
  spec_cluster_type: string;
  spec_machine_type: string;
  capacity: number;
  future_capacity?: number;
  qps?: {
    min: number;
    max: number;
  };
  shard_num?: number;
}) {
  return http
    .post<ClusterSpecModel[]>(`${path}/filter_cluster_spec/`, params)
    .then((data) => data.map((item) => new ClusterSpecModel(item)));
}

/**
 * 获取 qps 的范围
 */
export function queryQPSRange(params: {
  spec_cluster_type: string;
  spec_machine_type: string;
  capacity: number;
  future_capacity: number;
}) {
  return http.get<{
    max: number;
    min: number;
  }>(`${path}/query_qps_range/`, params);
}

/**
 * 获取推荐规格
 */
export function fetchRecommendSpec(
  params:
    | {
        cluster_id: number;
        role: string;
      }
    | {
        instance_id: number;
        role: string;
      },
) {
  return http
    .get<ResourceSpecModel[]>(`${path}/recommend_spec/`, params)
    .then((data) => data.map((item) => new ResourceSpecModel(item)));
}

/**
 * 校验规格名称是否重复
 */
export function verifyDuplicatedSpecName(params: {
  spec_cluster_type: string;
  spec_machine_type: string;
  spec_name: string;
  spec_id?: number;
}) {
  return http.post<boolean>(`${path}/verify_duplicated_spec_name/`, params);
}

/**
 * 规格详情
 */
export function getResourceSpec(params: { spec_id: number }) {
  return http.get<ResourceSpecModel>(`${path}/${params.spec_id}/`);
}

/**
 * 更新规格
 */
export function updateResourceSpec(
  params: Record<string, any> & {
    spec_id: number;
    spec_name: string;
    spec_cluster_type: string;
    spec_machine_type: string;
    enable?: boolean;
    device_class?: string[];
  },
) {
  return http.put<ResourceSpecModel>(`${path}/${params.spec_id}/`, params);
}

/**
 * 更新规格的启用禁用态
 */
export function updateResourceSpecEnableStatus(params: { spec_ids: number[]; enable: boolean }) {
  return http.post<ResourceSpecModel>(`${path}/modify_spec_enable_status/`, params);
}

/**
 * 删除规格
 */
export function deleteResourceSpec(params: { specId: number }) {
  return http.delete(`${path}/${params.specId}/`);
}
