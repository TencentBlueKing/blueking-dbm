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

import type {
  AccountTypesValues,
  ClusterTypes,
} from '@common/const';

import http from './http';
import type { ListBase } from './types/common';
import type {
  AccountRule,
  AuthorizePreCheckData,
  AuthorizePreCheckResult,
  CreateAccountParams,
  PasswordPolicy,
  PasswordStrength,
  PermissionCloneRes,
  PermissionRule,
  PermissionRulesParams,
  PermissionRulesResult,
} from './types/permission';

// 密码随机化周期
interface RamdomCycle {
  crontab: {
    minute: string,
    hour: string,
    day_of_week: string
    day_of_month: string
  }
}

// mysql生效实例密码(admin)
interface MysqlAdminPassword {
  component: string,
  id: number,
  ip: string,
  lock_until: string,
  operator: string,
  password: string,
  port: number,
  update_time: string,
  username: string
}

interface MysqlAdminPasswordResultItem {
  bk_cloud_id: number
  ip: string
  port: number
}

/**
 * 更新密码策略
 */
export interface PasswordPolicyParams {
  account_type: string,
  policy: PasswordPolicy
}

/**
 * 查询公钥参数
 */
export interface RSAPublicKeyParams {
  names: string[]
}

/**
 * 公钥信息
 */
export interface RSAPublicKey {
  content: string,
  description: string,
  name: string,
}

/**
 * 查询密码安全策略
 */
export const getPasswordPolicy = (accountType: string) => http.get<PasswordPolicy>('/apis/conf/password_policy/get_password_policy/', { account_type: accountType });

/**
 * 更新密码安全策略
 */
export const updatePasswordPolicy = (params: PasswordPolicyParams) => http.post<PasswordPolicyParams>('/apis/conf/password_policy/update_password_policy/', params);

/**
 * 查询随机化周期
 */
export const queryRandomCycle = () => http.get<RamdomCycle>('/apis/conf/password_policy/query_random_cycle/');

/**
 * 更新随机化周期
 */
export const modifyRandomCycle = (params: RamdomCycle) => http.post('/apis/conf/password_policy/modify_random_cycle/', params);

/**
 * 获取符合密码强度的字符串
 */
export const getRandomPassword = () => http.get<{
  password: string
}>('/apis/conf/password_policy/get_random_password/');

/**
 * 修改mysql实例密码(admin)
 */
export const modifyMysqlAdminPassword = (params: {
  lock_until: string
  password: string
  instance_list: {
    ip: string
    port: number
    bk_cloud_id: number
    cluster_type: ClusterTypes
    role: string
  }[]
}) => http.post<{
  success: MysqlAdminPasswordResultItem[] | null
  fail: MysqlAdminPasswordResultItem[] | null
}>('/apis/conf/password_policy/modify_mysql_admin_password/', params);

/**
 * 查询mysql生效实例密码(admin)
 */
export const queryMysqlAdminPassword = (params: {
  limit?: number
  offset?: number
  start_time: string
  end_time: string
  instance: string[]
}) => http.get<MysqlAdminPassword>('/apis/conf/password_policy/query_mysql_admin_password/', params).then(res => ({
  // TODO
  count: 100,
  next: '',
  previous: '',
  results: res,
}));

/**
 * 获取公钥列表
 */
export const getRSAPublicKeys = (params: RSAPublicKeyParams) => http.post<RSAPublicKey[]>('/apis/core/rsa/fetch_public_keys/', params);

/**
 * 校验密码强度
 */
export const verifyPasswordStrength = (bizId: number, password: string, accountType?: AccountTypesValues) => http.post<PasswordStrength>(`/apis/mysql/bizs/${bizId}/permission/account/verify_password_strength/`, { password, account_type: accountType });

/**
 * 查询账号规则列表
 */
export const getPermissionRules = (params: PermissionRulesParams) => http.get<PermissionRulesResult>(`/apis/mysql/bizs/${params.bk_biz_id}/permission/account/list_account_rules/`, params);

/**
 * 创建账户
 */
export const createAccount = (params: CreateAccountParams, bizId: number) => http.post(`/apis/mysql/bizs/${bizId}/permission/account/create_account/`, params);

/**
 * 删除账号
 */
export const deleteAccount = (bizId: number, accountId: number, accountType?: AccountTypesValues) => http.delete(`/apis/mysql/bizs/${bizId}/permission/account/delete_account/`, { account_id: accountId, account_type: accountType });

/**
 * 添加账号规则
 */
export const createAccountRule = (bizId: number, params: AccountRule) => http.post(`/apis/mysql/bizs/${bizId}/permission/account/add_account_rule/`, params);

/**
 * 授权规则前置检查
 */
export const preCheckAuthorizeRules = (bizId: number, params: AuthorizePreCheckData) => http.post<AuthorizePreCheckResult>(`/apis/mysql/bizs/${bizId}/permission/authorize/pre_check_rules/`, params);

/**
 * 查询账号规则
 */
export const queryAccountRules = (id: number, params: {user: string, access_dbs: string[], account_type?: AccountTypesValues}) => http.post<ListBase<PermissionRule[]>>(`/apis/mysql/bizs/${id}/permission/account/query_account_rules/`, params);

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
) => http.post<PermissionCloneRes>(`/apis/mysql/bizs/${bizId}/permission/clone/pre_check_clone/`, params);
