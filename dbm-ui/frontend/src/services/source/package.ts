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
import type { ListBase } from '../types/common';

const path = '/apis/packages';

/**
 * 版本信息
 */
export interface PackageItem {
  id: number,
  creator: string,
  create_at: string,
  updater: string,
  update_at: string,
  name: string,
  version: string,
  pkg_type: string,
  path: string,
  size: number,
  md5: string,
  allow_biz_ids: number[],
  mode: string
}

/**
 * 查询版本列表文件
 */
export const getPackages = function (params: {
  pkg_type: string,
  db_type: string,
  keyword: string,
  limit: number,
  offset: number,
}) {
  return http.get<ListBase<PackageItem[]>>(`${path}/`, params);
};

/**
 * 新建版本信息
 */
export interface NewPackageParams {
  name: string,
  version: string,
  pkg_type: string,
  db_type: string,
  path: string,
  size: number,
  md5: string,
  allow_biz_ids?: number[],
  mode?: string
}

/**
 * 新建版本
 */
export const createPackage = function (params: NewPackageParams) {
  return http.post<NewPackageParams>(`${path}/`, params);
};

/**
 * 删除版本
 */
export const deletePackage = function (params: { id: number }) {
  return http.delete(`${path}/${params.id}/`);
};
