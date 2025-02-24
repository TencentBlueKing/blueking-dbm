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

import SqlserverPermissionAccountModel from '@services/model/sqlserver/sqlserver-permission-account';
import type { ListBase } from '@services/types';

import type { AccountTypesValues } from '@common/const';

import http from '../http';

const getRootPath = () => `/apis/sqlserver/bizs/${window.PROJECT_CONFIG.BIZ_ID}/permission/account`;

/**
 * 添加账号规则
 */
export function addAccountRule(params: {
  access_db: string;
  account_id: number;
  account_type: AccountTypesValues;
  privilege: {
    sqlserver_dml?: string[];
    sqlserver_owner?: string[];
  };
}) {
  return http.post<null>(`${getRootPath()}/add_account_rule/`, params);
}

/**
 * 创建账号
 */
export function createAccount(params: { account_type?: AccountTypesValues; password: string; user: string }) {
  return http.post<null>(`${getRootPath()}/create_account/`, params);
}

/**
 * 删除账号
 */
export function deleteAccount(params: { account_id: number; account_type?: AccountTypesValues }) {
  return http.delete<null>(`${getRootPath()}/delete_account/`, params);
}

/**
 * 查询账号规则列表
 */
export function getPermissionRules(params: {
  access_dbs?: string;
  account_type?: AccountTypesValues;
  limit?: number;
  offset?: number;
  privilege?: string;
  user?: string;
}) {
  return http
    .get<ListBase<SqlserverPermissionAccountModel[]>>(`${getRootPath()}/list_account_rules/`, params)
    .then((res) => ({
      ...res,
      results: res.results.map((item) => new SqlserverPermissionAccountModel(item)),
    }));
}

/**
 * 查询账号规则
 */
export function queryAccountRules(params: { access_dbs: string[]; account_type?: AccountTypesValues; user: string }) {
  return http
    .post<ListBase<SqlserverPermissionAccountModel[]>>(`${getRootPath()}/query_account_rules/`, params)
    .then((res) => ({
      ...res,
      results: res.results.map((item) => new SqlserverPermissionAccountModel(item)),
    }));
}
