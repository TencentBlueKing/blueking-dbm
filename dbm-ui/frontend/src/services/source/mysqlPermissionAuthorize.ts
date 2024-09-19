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
import type { AuthorizePreCheckData, AuthorizePreCheckResult } from '@services/types/permission';

import http from '../http';

/**
 * 授权规则前置检查
 */
export const preCheckAuthorizeRules = (params: AuthorizePreCheckData & { bizId: number }) =>
  http.post<AuthorizePreCheckResult>(`/apis/mysql/bizs/${params.bizId}/permission/authorize/pre_check_rules/`, params);

/**
 * 权限克隆前置检查
 */
export const precheckPermissionClone = (params: {
  bizId: number;
  clone_type: 'instance' | 'client';
  clone_list: Array<{ source: string; target: string }>;
  clone_cluster_type: 'mysql' | 'tendbcluster';
}) =>
  http.post<{
    clone_data_list: Array<{
      message: string;
      source: string;
      target: Array<string> | string;
    }>;
    clone_uid: string;
    message: string;
    pre_check: boolean;
  }>(`/apis/mysql/bizs/${params.bizId}/permission/clone/pre_check_clone/`, params);
