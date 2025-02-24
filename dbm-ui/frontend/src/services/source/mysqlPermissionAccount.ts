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

import MysqlPermissionAccountModel from '@services/model/mysql/mysql-permission-account';
import type { ListBase } from '@services/types';
import type { AccountRule, CreateAccountParams, PermissionRule } from '@services/types/permission';

import type { AccountTypes, AccountTypesValues, ClusterTypes } from '@common/const';

import http, { type IRequestPayload } from '../http';

const getRootPath = () => `/apis/mysql/bizs/${window.PROJECT_CONFIG.BIZ_ID}/permission/account`;

/**
 * 查询账号规则列表
 */
export const getPermissionRules = (
  params: {
    access_db?: string;
    account_type?: AccountTypesValues;
    bk_biz_id: number;
    limit?: number;
    offset?: number;
    privilege?: string;
    rule_ids?: string;
    user?: string;
  },
  payload = {} as IRequestPayload,
) =>
  http
    .get<ListBase<MysqlPermissionAccountModel[]>>(`${getRootPath()}/list_account_rules/`, params, payload)
    .then((res) => ({
      ...res,
      results: res.results.map((item) => new MysqlPermissionAccountModel(item)),
    }));
/**
 * 创建账户
 */
export const createAccount = (params: CreateAccountParams) => http.post(`${getRootPath()}/create_account/`, params);

/**
 * 删除账号
 */
export const deleteAccount = (params: { account_id: number; account_type?: AccountTypesValues; bizId: number }) =>
  http.delete(`${getRootPath()}/delete_account/`, params);

/**
 * 添加账号规则
 */
export const createAccountRule = (params: { bk_biz_id: number } & AccountRule) =>
  http.post(`${getRootPath()}/add_account_rule/`, params);

/**
 * 修改账号规则
 */
export const modifyAccountRule = (
  params: {
    bk_biz_id: number;
    rule_id: number;
  } & AccountRule,
) => http.post(`${getRootPath()}/modify_account_rule/`, params);

/**
 * 查询账号规则
 */
export const queryAccountRules = (params: { access_dbs: string[]; account_type: AccountTypesValues; user: string }) =>
  http.post<ListBase<PermissionRule[]>>(`${getRootPath()}/query_account_rules/`, params);

/**
 * 添加账号规则前置检查
 */
export const preCheckAddAccountRule = (params: {
  access_db: string;
  account_id: number | null;
  account_type: AccountTypesValues;
  privilege: {
    ddl: string[];
    dml: string[];
    glob: string[];
  };
}) =>
  http.post<{
    force_run: boolean;
    warning: string | null;
  }>(`${getRootPath()}/pre_check_add_account_rule/`, params);

interface PrivsForIp {
  dbs: Array<{
    db: string;
    domains: Array<{
      immute_domain: string;
      users: Array<{
        match_ips: Array<{
          match_dbs: Array<{
            match_db: string;
            priv: string;
          }>;
          match_ip: string;
        }>;
        user: string;
      }>;
    }>;
  }>;
  ip: string;
}

interface PrivsForCluster {
  immute_domain: string;
  users: Array<{
    match_ips: Array<{
      match_dbs: Array<{
        ip_dbs: Array<{
          db: string;
          ip: string;
        }>;
        match_db: string;
        priv: string;
      }>;
      match_ip: string;
    }>;
    user: string;
  }>;
}

/**
 * 查询权限清单
 */
export const getAccountPrivs = (params: {
  account_type: AccountTypes;
  cluster_type: ClusterTypes;
  dbs?: string;
  format_type?: string; // 'ip' | 'cluster';
  immute_domains: string;
  ips: string;
  limit?: number;
  offset?: number;
  users: string;
}) =>
  http.get<{
    match_ips_count: number;
    results: {
      has_priv: string[] | null;
      no_priv: string[] | null;
      privs_for_cluster: PrivsForCluster[] | null;
      privs_for_ip: PrivsForIp[] | null;
    };
  }>(`${getRootPath()}/get_account_privs/`, params);

/**
 * 下载权限清单
 */
export const getDownloadPrivs = (params: {
  account_type: AccountTypes;
  cluster_type: ClusterTypes;
  dbs?: string;
  format_type?: string; // 'ip' | 'cluster';
  immute_domains: string;
  ips: string;
  users: string;
}) => http.get<string>(`${getRootPath()}/get_download_privs/`, params, { responseType: 'blob' });

/**
 * 查询用户列表
 */
export const getAccountUsers = (params: {
  account_type: AccountTypes;
  cluster_type: ClusterTypes;
  immute_domains: string;
  ips: string;
  limit?: number;
  offset?: number;
}) => http.get<ListBase<string[]>>(`${getRootPath()}/get_account_users/`, params);
