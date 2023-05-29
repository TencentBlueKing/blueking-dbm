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

export function fetchList(params: Record<string, any>) {
  return http.post('/apis/dbresource/resource/list/', params);
}

export function importResource(params: Record<string, any>) {
  return http.post('/apis/dbresource/resource/import/', params);
}

// 获取磁盘类型
export function fetchDiskTypes() {
  return http.get<{code: number, request_id: string}[]>('/apis/dbresource/resource/get_disktypes/');
}

// 获取挂载点
export function fetchMountPoints() {
  return http.get<{code: number, request_id: string}[]>('/apis/dbresource/resource/get_mountpoints/');
}

// 根据逻辑城市查询园区
export function fetchSubzones(params: {citys: string}) {
  return http.get<string[]>('/apis/dbresource/resource/get_subzones/', params);
}
