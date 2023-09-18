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

import http from './http';
import type { ListBase } from './types/common';
import type {
  AccountRule,
  AuthorizePreCheckData,
  AuthorizePreCheckResult,
  CreateAccountParams,
  PasswordPolicy,
  PasswordPolicyParams,
  PasswordStrength,
  PermissionCloneRes,
  PermissionRule,
  PermissionRulesParams,
  PermissionRulesResult,
  RSAPublicKey,
  RSAPublicKeyParams } from './types/permission';

/**
 * 查询密码安全策略
 */
export const getPasswordPolicy = (accountType: string): Promise<PasswordPolicy> => http.get('/apis/conf/password_policy/get_password_policy/', { account_type: accountType });

/**
 * 更新密码安全策略
 */
export const updatePasswordPolicy = (params: PasswordPolicyParams): Promise<PasswordPolicyParams> => http.post('/apis/conf/password_policy/update_password_policy/', params);

/**
 * 查询账号规则列表
 */
export const getPermissionRules = (params: PermissionRulesParams): Promise<PermissionRulesResult> => http.get(`/apis/mysql/bizs/${params.bk_biz_id}/permission/account/list_account_rules/`, params);

/**
 * 创建账户
 */
export const createAccount = (params: CreateAccountParams, bizId: number) => http.post(`/apis/mysql/bizs/${bizId}/permission/account/create_account/`, params);

/**
 * 删除账号
 */
export const deleteAccount = (bizId: number, accountId: number, accountType?: AccountTypesValues) => http.delete(`/apis/mysql/bizs/${bizId}/permission/account/delete_account/`, { account_id: accountId, account_type: accountType });

/**
 * 获取公钥列表
 */
export const getRSAPublicKeys = (params: RSAPublicKeyParams): Promise<RSAPublicKey[]> => http.post('/apis/core/rsa/fetch_public_keys/', params);

/**
 * 校验密码强度
 */
export const verifyPasswordStrength = (bizId: number, password: string, accountType?: AccountTypesValues): Promise<PasswordStrength> => http.post(`/apis/mysql/bizs/${bizId}/permission/account/verify_password_strength/`, { password, account_type: accountType });

/**
 * 添加账号规则
 */
export const createAccountRule = (bizId: number, params: AccountRule) => http.post(`/apis/mysql/bizs/${bizId}/permission/account/add_account_rule/`, params);

/**
 * 授权规则前置检查
 */
export const preCheckAuthorizeRules = (bizId: number, params: AuthorizePreCheckData): Promise<AuthorizePreCheckResult> => http.post(`/apis/mysql/bizs/${bizId}/permission/authorize/pre_check_rules/`, params);

/**
 * 查询账号规则
 */
export const queryAccountRules = (id: number, params: {user: string, access_dbs: string[], account_type?: AccountTypesValues}): Promise<ListBase<PermissionRule[]>> => http.post(`/apis/mysql/bizs/${id}/permission/account/query_account_rules/`, params);

/**
 * 权限克隆前置检查
 */
export const precheckPermissionClone = (
  bizId: number,
  params: {
    clone_type: 'instance' | 'client',
    clone_list: Array<{source: string, target: string}>,
    clone_cluster_type: 'mysql'|'tendbcluster'
  },
): Promise<PermissionCloneRes> => http.post(`/apis/mysql/bizs/${bizId}/permission/clone/pre_check_clone/`, params);
