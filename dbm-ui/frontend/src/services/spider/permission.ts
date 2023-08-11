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

import type { PasswordStrength } from '@services/types/permission';

import { useGlobalBizs } from '@stores';

import type { AccountTypesValues } from '@common/const';

import http from '../http';
import type { ListBase } from '../types/common';

const { currentBizId } = useGlobalBizs();

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
 * 用户账号规则
 */
export interface PermissionRule {
  account: PermissionRuleAccount,
  rules: PermissionRuleInfo[]
}

/**
 * 用户账号规则 - 账户信息
 */
export interface PermissionRuleAccount {
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
export interface PermissionRuleInfo {
  access_db: string
  account_id: number
  bk_biz_id: number
  create_time: string
  creator: string
  privilege: string
  rule_id: number
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
  account_type?: AccountTypesValues
}

/**
 * 查询账号规则列表返回结果
 */
export type PermissionRulesResult =  ListBase<Permission[]>

/**
 * 新增账号规则
 */
export interface AccountRule {
  access_db: string,
  privilege: AccountRulePrivilege,
  account_id: number | null,
  account_type?: AccountTypesValues
}

/**
 * 新增账号规则 - 权限信息
 */
export interface AccountRulePrivilege {
  ddl: string[],
  dml: string[],
  glob: string[]
}

/**
 * 用户账号规则 - 账户信息
 */
export interface PermissionRuleAccount {
  account_id: number,
  bk_biz_id: number,
  user: string
  creator: string,
  create_time: string,
  password: string
}

/**
 * 查询账号规则列表
 */
export const getPermissionList = (params: PermissionRulesParams) => http.get<PermissionRulesResult>(`/apis/mysql/bizs/${currentBizId}/permission/account/list_account_rules/`, params);

/**
 * 创建账号
 */
export const createAccount = (params: { user: string, password: string, account_type: AccountTypesValues }) => http.post(`/apis/mysql/bizs/${currentBizId}/permission/account/create_account/`, params);

/**
 * 删除账号
 */
export const deleteAccount = (params: { account_id: number, account_type: AccountTypesValues }) => http.delete(`/apis/mysql/bizs/${currentBizId}/permission/account/delete_account/`, params);

/**
 * 校验密码强度
 */
export const verifyPasswordStrength = (params: { password: string, account_type: AccountTypesValues }) => http.post<PasswordStrength>(`/apis/mysql/bizs/${currentBizId}/permission/account/verify_password_strength/`, params);

/**
 * 添加账号规则
 */
export const createAccountRule = (params: AccountRule) => http.post(`/apis/mysql/bizs/${currentBizId}/permission/account/add_account_rule/`, params);

/**
 * 查询账号规则列表
 */
export const getPermissionRules = (params: PermissionRulesParams) => http.get<PermissionRulesResult>(`/apis/mysql/bizs/${currentBizId}/permission/account/list_account_rules/`, params);

/**
 * 查询账号规则
 */
export const queryAccountRules = (params: { user: string, access_dbs: string[], account_type: AccountTypesValues}) => http.post<ListBase<PermissionRule[]>>(`/apis/mysql/bizs/${currentBizId}/permission/account/query_account_rules/`, params);
