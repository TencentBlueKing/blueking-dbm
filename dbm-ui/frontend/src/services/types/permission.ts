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

import type { ListBase } from './index';

/**
 * 查询账号规则列表返回结果
 */
export type PermissionRulesResult = ListBase<PermissionRule[]>;

/**
 * 用户账号规则
 */
export interface PermissionRule {
  account: PermissionRuleAccount;
  permission: Record<string, boolean>;
  rules: PermissionRuleInfo[];
}

/**
 * 用户账号规则 - 账户信息
 */
export interface PermissionRuleAccount {
  account_id: number;
  bk_biz_id: number;
  create_time: string;
  creator: string;
  password: string;
  user: string;
}

/**
 * 用户账号规则信息
 */
export interface PermissionRuleInfo {
  access_db: string;
  account_id: number;
  bk_biz_id: number;
  create_time: string;
  creator: string;
  priv_ticket: {
    action: 'delete' | 'change';
    ticket_id: number;
  };
  privilege: string;
  rule_id: number;
}

/**
 * 创建账户
 */
export interface CreateAccountParams {
  account_type?: AccountTypesValues;
  password: string;
  user: string;
}

/**
 * 密码强度
 */
export interface PasswordStrength {
  is_strength: boolean;
  password_verify_info: PasswordStrengthVerifyInfo;
}
/**
 * 密码强度校验项
 */
export interface PasswordStrengthVerifyInfo {
  allowed_valid: boolean;
  follow_keyboards_valid: boolean;
  follow_letters_valid: boolean;
  follow_numbers_valid: boolean;
  follow_symbols_valid: boolean;
  max_length_valid: boolean;
  min_length_valid: boolean;
  number_of_types_valid: boolean;
  out_of_range: string;
  repeats_valid: boolean;
}

// 密码策略
export interface PasswordPolicy {
  create_time?: string;
  creator?: string;
  id: number;
  name: string;
  operator?: string;
  rule: {
    include_rule: PasswordPolicyIncludeRule;
    max_length: number;
    min_length: number;
    number_of_types: number;
    repeats: number;
    symbols_allowed: string;
    weak_password: boolean;
  };
  update_time?: string;
}

// 密码策略 include_rule
export interface PasswordPolicyIncludeRule {
  lowercase: boolean;
  numbers: boolean;
  symbols: boolean;
  uppercase: boolean;
}

/**
 * 新增账号规则 - 权限信息
 */
export interface AccountRulePrivilege {
  ddl: string[];
  dml: string[];
  glob: string[];
}

export type AccountRulePrivilegeKey = keyof AccountRulePrivilege;

/**
 * 新增账号规则
 */
export interface AccountRule {
  access_db: string;
  account_id: number | null;
  account_type?: AccountTypesValues;
  privilege: AccountRulePrivilege;
}

/**
 * 规则授权前置检查信息
 */
export interface AuthorizePreCheckData {
  access_dbs: string[];
  bk_biz_id?: number;
  cluster_ids?: number[];
  cluster_type: string;
  privileges?: {
    access_db: string;
    priv: string;
    user: string;
  }[];
  source_ips?:
    | {
        bk_host_id?: number;
        ip: string;
      }[]
    | string[];
  target_instances: string[];
  user: string;
}

/**
 * 规则授权前置检查返回结果
 */
export interface AuthorizePreCheckResult {
  authorize_data: AuthorizePreCheckData;
  authorize_data_list: AuthorizePreCheckData[];
  authorize_uid: string;
  excel_url?: string;
  message: string;
  pre_check: boolean;
  task_index: number;
}
