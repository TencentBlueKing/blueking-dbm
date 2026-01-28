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

import DbVersionModel from '@services/model/version-file/db-version';
import ReleaseVersionModel from '@services/model/version-file/release-version';

import http, { type IRequestPayload } from '../http';

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
export function getVersions(
  params: {
    db_type?: string;
    query_key: string;
  },
  payload = {} as IRequestPayload,
) {
  return http.get<string[]>(`${path}/list_versions/`, params, payload);
}

/**
 * 获取项目版本
 */
export function getProjectVersion() {
  return http.get<{
    app_version: string;
    chart_version: string;
    version: string;
  }>('/version/');
}

/**
 * 根据sqlserver部署版本查询可支持的系统版本
 */
export function listSqlserverSystemVersion(params: { limit?: number; offset?: number; sqlserver_version: string }) {
  return http.get<string[]>(`${path}/list_sqlserver_system_version/`, params);
}

/**
 * mysql存储引擎列表
 */
export function getMysqlEngineList(params?: { limit?: number; offset?: number }) {
  return http.get<string[]>(`${path}/list_mysql_engine/`, params);
}

/**
 * 发行版列表
 */
export function getReleaseVersionList(params: { db_type: string; engine?: string; name?: string; pkg_type: string }) {
  return http
    .get<ReleaseVersionModel[]>(`${path}/distribution/`, params, { cache: 3000 })
    .then((data) => data.map((item) => new ReleaseVersionModel(item)));
}

/**
 * 新建发行版
 */
export function createReleaseVersion(params: { db_type: string; engine?: string; name?: string; pkg_type: string }) {
  return http.post<{ id: number }>(`${path}/distribution/`, params);
}

/**
 * 更新发行版
 */
export function updateReleaseVersion(params: {
  db_type: string;
  engine?: string;
  id: number;
  name?: string;
  pkg_type: string;
}) {
  return http.patch<{ id: number }>(`${path}/distribution/${params.id}/`, params);
}

/**
 * 删除发行版
 */
export function deleteReleaseVersion(params: {
  db_type: string;
  engine?: string;
  id: number;
  name?: string;
  pkg_type: string;
}) {
  return http.delete<null>(`${path}/distribution/${params.id}/`, params);
}

/**
 * 介质版本列表
 */
export function getDbVersionList(params: { version_series__in: string }) {
  return http.get<DbVersionModel[]>(`${path}/dbversion/`, params);
}

/**
 * 新增介质版本
 */
export function createDbVersion(params: {
  description?: string;
  distribution_snapshot?: {
    db_type: string;
    engine: string;
    id: number;
    name: string;
    pkg_type: string;
  };
  enable?: boolean;
  full_version?: string;
  name?: string;
  phase: string;
  recommend?: boolean;
  version_series?: number;
}) {
  return http.post<{
    id: number;
    name: string;
  }>(`${path}/dbversion/`, params);
}

/**
 * 更新介质版本
 */
export function updateDbVersion(params: {
  description?: string;
  distribution_snapshot?: {
    db_type: string;
    engine: string;
    id: number;
    name: string;
    pkg_type: string;
  };
  enable?: boolean;
  full_version?: string;
  id: number;
  name?: string;
  phase: string;
  recommend?: boolean;
  version_series?: number;
}) {
  return http.patch<{
    id: number;
    name: string;
  }>(`${path}/dbversion/${params.id}/`, params);
}

/**
 * 删除介质版本
 */
export function deleteDbVersion(params: { id: number }) {
  return http.delete<null>(`${path}/dbversion/${params.id}/`);
}

/**
 * 版本系列列表
 */
export function getVersionSeriesList(params: { distribution: number }) {
  return http.get<
    {
      create_at: string;
      creator: string;
      distribution: number;
      id: number;
      name: string;
      update_at: string;
      updater: string;
    }[]
  >(`${path}/version_series/`, params);
}

/**
 * 新增版本系列
 */
export function createVersionSeries(params: { distribution?: number; name?: string }) {
  return http.post<{ id: number; name: string }>(`${path}/version_series/`, params);
}

/**
 * 更新版本系列
 */
export function updateVersionSeries(params: { distribution?: number; id: number; name?: string }) {
  return http.put<{ id: number; name: string }>(`${path}/version_series/${params.id}/`, params);
}

/**
 * 删除版本系列
 */
export function deleteVersionSeries(params: { distribution: number; id: number }) {
  return http.delete<null>(`${path}/version_series/${params.id}/`, params);
}
