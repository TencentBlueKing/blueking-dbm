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

/**
 * 用户账号规则
 */
export interface Permission {
  account: PermissionAccount,
  rules: PermissionInfo[]
}

/**
 * 用户账号规则 - 账户信息
 */
export interface PermissionAccount {
  account_id: number,
  bk_biz_id: number,
  user: string
  creator: string,
  create_time: string,
  password: string
}

/**
 * 用户账号规则信息
 */
export interface PermissionInfo {
  access_db: string
  account_id: number
  bk_biz_id: number
  create_time: string
  creator: string
  privilege: string
  rule_id: number
  instance: string
}

/**
 * 查询账号规则列表参数
 */
export interface PermissionRulesParams {
  limit?: number,
  offset?: number,
  bk_biz_id: number,
  user?: string,
  access_db?: string,
  privilege?: string,
}

/**
 * 查询账号规则列表返回结果
 */
export type PermissionRulesResult =  ListBase<Permission[]>

/**
 * 查询账号规则列表
 */
export const getPermissionList = (params: PermissionRulesParams): Promise<PermissionRulesResult> => http.get(`/apis/mysql/bizs/${params.bk_biz_id}/permission/account/list_account_rules/`, params);
