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

import SqlserverPermissonAccountModel from '@services/model/sqlserver/sqlserver-permission';

import { useGlobalBizs } from '@stores';

import type { AccountTypesValues } from '@common/const';

import http from '../http';
import type { ListBase } from '../types';

const { currentBizId } = useGlobalBizs();

const path = `/apis/mongodb/bizs/${currentBizId}/permission/account`;

/**
 * 添加账号规则
 */
export function addSqlserverAccountRule(params: {
  access_db: string,
  privilege: string[],
  account_id: number | null,
}) {
  return http.post<null>(`${path}/add_account_rule/`, params);
}

/**
 * 创建账号
 */
export function createSqlserverAccount(params: {
  user: string,
  password: string,
  account_type?: AccountTypesValues
}) {
  return http.post<null>(`${path}/create_account/`, params);
}

/**
 * 删除账号
 */
export function deleteSqlserverAccount(params: {
  account_id: number,
  account_type?: AccountTypesValues
}) {
  return http.delete<null>(`${path}/delete_account/`, params);
}

/**
 * 查询账号规则列表
 */
export function getSqlserverPermissionRules(params: {
  limit?: number,
  offset?: number,
  user?: string,
  access_db?: string,
  privilege?: string,
  account_type?: AccountTypesValues
}) {
  return http.get<ListBase<SqlserverPermissonAccountModel[]>>(`${path}/list_account_rules/`, params)
    .then(res => ({
      ...res,
      results: res.results.map(item => new SqlserverPermissonAccountModel(item)),
    }));
}

/**
 * 查询账号规则
 */
export function querySqlserverAccountRules(params: {
  user: string,
  access_dbs: string[],
  account_type?: AccountTypesValues
}) {
  return http.post<ListBase<SqlserverPermissonAccountModel[]>>(`${path}/query_account_rules/`, params)
    .then(res => ({
      ...res,
      results: res.results.map(item => new SqlserverPermissonAccountModel(item)),
    }));
}
