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

import MongodbPermissonAccountModel from '@services/model/mongodb/mongodb-permission-account';
import type { ListBase } from '@services/types';

import type { AccountTypesValues } from '@common/const';

import http, { type IRequestPayload } from '../http';

const getRootPath = () => `/apis/mongodb/bizs/${window.PROJECT_CONFIG.BIZ_ID}/permission/account`;

/**
 * 添加账号规则
 */
export function addAccountRule(params: {
  access_db: string;
  privilege: {
    mongo_user: string[];
    mongo_manager: string[];
  };
  account_id: number | null;
  account_type: AccountTypesValues;
}) {
  return http.post<null>(`${getRootPath()}/add_account_rule/`, params);
}

/**
 * 创建账号
 */
export function createAccount(params: { user: string; password: string; account_type?: AccountTypesValues }) {
  return http.post<null>(`${getRootPath()}/create_account/`, params);
}

/**
 * 删除账号
 */
export function deleteAccount(params: { bizId: number; account_id: number; account_type?: AccountTypesValues }) {
  return http.delete<null>(`${getRootPath()}/delete_account/`, params);
}

/**
 * 查询账号规则列表
 */
export function getPermissionRules(
  params: {
    limit?: number;
    offset?: number;
    user?: string;
    access_db?: string;
    privilege?: string;
    account_type?: AccountTypesValues;
  },
  payload = {} as IRequestPayload,
) {
  return http
    .get<ListBase<MongodbPermissonAccountModel[]>>(`${getRootPath()}/list_account_rules/`, params, payload)
    .then((res) => ({
      ...res,
      results: res.results.map((item) => new MongodbPermissonAccountModel(item)),
    }));
}

/**
 * 查询账号规则
 */
export function queryAccountRules(params: { user: string; access_dbs: string[]; account_type?: AccountTypesValues }) {
  return http
    .post<ListBase<MongodbPermissonAccountModel[]>>(`${getRootPath()}/query_account_rules/`, params)
    .then((res) => ({
      ...res,
      results: res.results.map((item) => new MongodbPermissonAccountModel(item)),
    }));
}
