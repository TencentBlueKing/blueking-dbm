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

import type { AccountTypesValues } from '@common/const';

import http, { type IRequestPayload } from '../http';

const getRootPath = () => `/apis/mysql/bizs/${window.PROJECT_CONFIG.BIZ_ID}/permission/account`;

/**
 * 查询账号规则列表
 */
export const getPermissionRules = (
  params: {
    limit?: number;
    offset?: number;
    bk_biz_id: number;
    rule_ids?: string;
    user?: string;
    access_db?: string;
    privilege?: string;
    account_type?: AccountTypesValues;
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
export const deleteAccount = (params: { bizId: number; account_id: number; account_type?: AccountTypesValues }) =>
  http.delete(`${getRootPath()}/delete_account/`, params);

/**
 * 添加账号规则
 */
export const createAccountRule = (params: AccountRule & { bk_biz_id: number }) =>
  http.post(`${getRootPath()}/add_account_rule/`, params);

/**
 * 修改账号规则
 */
export const modifyAccountRule = (
  params: AccountRule & {
    rule_id: number;
    bk_biz_id: number;
  },
) => http.post(`${getRootPath()}/modify_account_rule/`, params);

/**
 * 查询账号规则
 */
export const queryAccountRules = (params: { user: string; access_dbs: string[]; account_type: AccountTypesValues }) =>
  http.post<ListBase<PermissionRule[]>>(`${getRootPath()}/query_account_rules/`, params);

/**
 * 添加账号规则前置检查
 */
export const preCheckAddAccountRule = (params: {
  account_id: number | null;
  access_db: string;
  privilege: {
    dml: string[];
    ddl: string[];
    glob: string[];
  };
  account_type: AccountTypesValues;
}) =>
  http.post<{
    force_run: boolean;
    warning: string | null;
  }>(`${getRootPath()}/pre_check_add_account_rule/`, params);
