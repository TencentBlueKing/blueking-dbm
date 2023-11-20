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

import type { AccountTypesValues } from '@common/const';

import type { HostNodeForSubmit, ListBase } from './common';

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
export type PermissionRulesResult = ListBase<PermissionRule[]>

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
 * 创建账户
 */
export interface CreateAccountParams {
  user: string,
  password: string,
  account_type?: AccountTypesValues
}

/**
 * 密码强度
 */
export interface PasswordStrength {
  is_strength: boolean,
  password_verify_info: PasswordStrengthVerifyInfo
}
/**
 * 密码强度校验项
 */
export interface PasswordStrengthVerifyInfo {
  follow_keyboards_valid: boolean,
  follow_letters_valid: boolean,
  follow_numbers_valid: boolean,
  follow_symbols_valid: boolean,
  lowercase_valid: boolean,
  max_length_valid: boolean,
  min_length_valid: boolean,
  numbers_valid: boolean,
  repeats_valid: boolean,
  symbols_valid: boolean,
  uppercase_valid: boolean
}

// 密码策略
export interface PasswordPolicy {
  id: number,
  name: string,
  rule: {
    include_rule: PasswordPolicyIncludeRule
    exclude_continuous_rule: PasswordPolicyExcludeContinuousRule,
    max_length: number,
    min_length: number,
  },
  creator?: string,
  create_time?: string,
  operator?: string,
  update_time?: string
}

// 密码策略 include_rule
export interface PasswordPolicyIncludeRule {
  numbers: boolean,
  symbols: boolean,
  lowercase: boolean,
  uppercase: boolean
}

// 密码策略 exclude_continuous_rule
export interface PasswordPolicyExcludeContinuousRule {
  limit: number,
  letters: boolean,
  numbers: boolean,
  repeats: boolean,
  symbols: boolean,
  keyboards: boolean
}

// 密码策略 include_rule
export interface PasswordPolicyIncludeRule {
  numbers: boolean,
  symbols: boolean,
  lowercase: boolean,
  uppercase: boolean
}

// 密码策略 exclude_continuous_rule
export interface PasswordPolicyExcludeContinuousRule {
  limit: number,
  letters: boolean,
  numbers: boolean,
  repeats: boolean,
  symbols: boolean,
  keyboards: boolean
}

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
 * 规则授权前置检查信息
 */
export interface AuthorizePreCheckData {
  access_dbs: string[],
  source_ips: HostNodeForSubmit[],
  target_instances: string[],
  user: string,
  cluster_type: string,
  cluster_ids?: number[],
}

/**
 * 规则授权前置检查返回结果
 */
export interface AuthorizePreCheckResult {
  authorize_uid: string,
  excel_url?: string,
  authorize_data: AuthorizePreCheckData,
  message: string,
  pre_check: boolean,
  task_index: number,
  authorize_data_list: AuthorizePreCheckData[],
}

/**
 * 实例权限克隆
 */
export interface PermissionCloneRes {
  clone_data_list: Array<{
    message: string,
    source: string,
    target: Array<string> | string
  }>,
  clone_uid: string,
  message: string,
  pre_check: boolean
}
