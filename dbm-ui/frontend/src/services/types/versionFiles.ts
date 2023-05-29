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

/**
 * 查询版本列表参数
 */
export interface GetPackagesParams {
  pkg_type: string,
  db_type: string,
  keyword: string,
  limit: number,
  offset: number,
}

/**
 * 查询版本列表返回结果
 */
export interface PackagesResult {
  count: number,
  next: string,
  previous: string,
  results: PackageItem[]
}

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
 * 获取数据库版本列表
 */
export interface GetVersionsParams {
  query_key: string,
  db_type?: string
}

/**
 * 文件上传参数
 */
export interface UploadParams {
  file: any,
  version: string,
  pkg_type: string,
  db_type: string
}

/**
 * 文件上传返回结果
 */
export interface UploadResult {
  md5: string,
  name: string,
  path: string,
  size: number
}
