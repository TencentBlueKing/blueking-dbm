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

import type { ClusterStateSchema } from '@services/types';

import type { ClusterTypes } from '@common/const';

import http from '../http';

const path = '/apis/cluster_state';

// 按业务 + 集群类型缓存字段定义。不用 http 的 cache：它会把失败的请求一并缓存，接口失败一次后刷新页面前都拿不到字段
const schemaCache = new Map<string, Promise<ClusterStateSchema>>();

/**
 * 获取集群类型的状态字段定义与默认展示列
 */
export function getClusterStateSchema(params: { bk_biz_id: number; cluster_type: ClusterTypes }) {
  const cacheKey = `${params.bk_biz_id}_${params.cluster_type}`;
  let request = schemaCache.get(cacheKey);
  if (!request) {
    request = http
      .get<ClusterStateSchema>(`${path}/bizs/${params.bk_biz_id}/schema/`, {
        cluster_type: params.cluster_type,
      })
      .catch((error) => {
        // 失败时移除缓存，下次调用重新请求
        schemaCache.delete(cacheKey);
        return Promise.reject(error);
      });
    schemaCache.set(cacheKey, request);
  }
  return request;
}
