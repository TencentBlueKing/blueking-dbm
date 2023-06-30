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


// 获取资源规格列表
export const getResourceSpecList = function (params:  Record<string, any> & {
  spec_cluster_type: string,
  spec_machine_type: string,
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
export const batchDeleteResourceSpec = function (params: Record<string, any> & {spec_ids: number[]}) {
  return http.delete('/apis/dbresource/spec/batch_delete/', params, {});
};

// 删除规格
export const deleteResourceSpec = function (specId: number) {
  return http.delete(`/apis/dbresource/spec/${specId}/`);
};
