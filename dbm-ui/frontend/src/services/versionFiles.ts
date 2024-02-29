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
import type { GetPackagesParams, GetVersionsParams, NewPackageParams, PackagesResult } from './types/versionFiles';

/**
 * 查询版本列表文件
 */
export const getPackages = (params: GetPackagesParams) => http.get<PackagesResult>('/apis/packages/', params);

/**
 * 新建版本
 */
export const createPackage = (params: NewPackageParams) => http.post<NewPackageParams>('/apis/packages/', params);

/**
 * 删除版本
 */
export const deletePackage = (params: { id: number }) => http.delete(`/apis/packages/${params.id}/`);

/**
 * 查询数据库版本列表
 */
export const getVersions = (params: GetVersionsParams) => http.get<string[]>('/apis/version/list_versions/', params);
