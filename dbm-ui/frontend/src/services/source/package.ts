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

import VersionFileModel from '@services/model/version-file/version-file';

import http, {
  type IRequestPayload,
} from '../http';
import type { ListBase } from '../types';

const path = '/apis/packages';

/**
 * 查询版本列表文件
 */
export function getPackages(params: {
  pkg_type: string,
  db_type: string,
  keyword: string,
  limit: number,
  offset: number,
}, payload = {} as IRequestPayload) {
  return http.get<ListBase<VersionFileModel[]>>(`${path}/`, params, payload)
    .then(data => ({
      ...data,
      results: data.results.map(item => new VersionFileModel(Object.assign(item, {
        permission: data.permission,
      }))),
    }));
}

/**
 * 新建版本信息
 */
interface NewPackageParams {
  name: string,
  version: string,
  pkg_type: string,
  db_type: string,
  path: string,
  size: number,
  md5: string,
  allow_biz_ids?: number[],
  mode?: string,
}

/**
 * 新建版本
 */
export function createPackage(params: NewPackageParams) {
  return http.post<NewPackageParams>(`${path}/`, params);
}

/**
 * 删除版本
 */
export function deletePackage(params: { id: number }) {
  return http.delete(`${path}/${params.id}/`);
}

/**
 * 更新版本文件属性
 */
export function updatePackage(params: Partial<NewPackageParams> & {
  id: number,
  priority?: number,
  enable?: boolean,
}) {
  return http.patch<NewPackageParams>(`${path}/${params.id}/`, params);
}

/**
 * 查询组件安装包列表
 */
export function listPackages(params: {
  db_type: string,
  query_key: string,
  limit?: number,
  offset?: number,
}) {
  return http.get<string[]>(`${path}/list_install_packages/`, params);
}

/**
 * 查询组件安装包类型
 */
export function listPackageTypes(params: {
  keyword?: string,
  db_type?: string,
  pkg_type?: string,
  version?: string,
  limit?: number,
  offset?: number,
}) {
  return http.get<Record<string, string[]>>(`${path}/list_install_pkg_types/`, params);
}
