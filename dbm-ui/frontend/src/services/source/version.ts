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

const path = '/apis/version';

/**
 * 查询所有数据库的版本列表
 */
export function getClusterTypeToVersions() {
  return http.get<Record<string, string[]>>(`${path}/cluster_type_to_versions/`);
}

/**
 * 查询数据库版本列表
 */
export function getVersions(params: {
  query_key: string,
  db_type?: string
}) {
  return http.get<string[]>(`${path}/list_versions/`, params);
}

/**
 * 获取项目版本
 */
export function getProjectVersion() {
  return http.get<{
    app_version: string,
    chart_version: string,
    version: string,
  }>('/version/');
}
