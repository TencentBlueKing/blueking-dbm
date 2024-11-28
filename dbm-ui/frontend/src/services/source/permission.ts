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
import AdminPasswordModel from '@services/model/admin-password/admin-password';
import type { ListBase } from '@services/types';

import type { ClusterTypes, DBTypes } from '@common/const';

import http, { type IRequestPayload } from '../http';
import type { PasswordPolicy, PasswordStrength } from '../types/permission';

// 密码随机化周期
interface RamdomCycle {
  crontab: {
    minute: string;
    hour: string;
    day_of_week: string;
    day_of_month: string;
  };
}

interface AdminPasswordResultItem {
  bk_cloud_id: number;
  cluster_type: ClusterTypes;
  instances: {
    role: string;
    addresses: {
      ip: string;
      port: number;
    }[];
  }[];
}

const path = '/apis/conf/password_policy';

/**
 * 查询密码安全策略
 */
export const getPasswordPolicy = (params: { name: string }) =>
  http.get<PasswordPolicy>(`${path}/get_password_policy/`, params);

/**
 * 更新密码安全策略
 */
export const updatePasswordPolicy = (params: PasswordPolicy & { reset: boolean }) =>
  http.post(`${path}/update_password_policy/`, params);

/**
 * 查询随机化周期
 */
export const queryRandomCycle = (params = {}, payload = {} as IRequestPayload) =>
  http.get<RamdomCycle>(`${path}/query_random_cycle/`, params, payload);

/**
 * 更新随机化周期
 */
export const modifyRandomCycle = (params: RamdomCycle) => http.post(`${path}/modify_random_cycle/`, params);

/**
 * 获取符合密码强度的字符串
 */
export const getRandomPassword = (params?: { security_type: string }) =>
  http.get<{
    password: string;
  }>(`${path}/get_random_password/`, params);

/**
 * 修改实例密码(admin)
 */
export const modifyAdminPassword = (params: {
  lock_hour: number;
  password: string;
  instance_list: {
    ip: string;
    port: number;
    bk_cloud_id: number;
    cluster_type: ClusterTypes;
    role: string;
  }[];
  // 是否异步
  is_async?: boolean;
}) => http.post<string>(`${path}/modify_admin_password/`, params);

/**
 * 查询生效实例密码(admin)
 */
export const queryAdminPassword = (params: {
  limit?: number;
  offset?: number;
  begin_time?: string;
  end_time?: string;
  instances?: string;
  db_type?: DBTypes;
}) =>
  http.post<ListBase<AdminPasswordModel[]>>(`${path}/query_admin_password/`, params).then((res) => ({
    ...res,
    results: res.results.map((item) => new AdminPasswordModel(item)),
  }));

/**
 * 查询异步密码修改执行结果
 */
export const queryAsyncModifyResult = (params: { root_id: string }) =>
  http.post<{
    status: string;
    error?: string;
    success?: AdminPasswordResultItem[];
    fail?: AdminPasswordResultItem[];
    result?: boolean;
  }>(`${path}/query_async_modify_result/`, params);

/**
 * 获取公钥列表
 */
export const getRSAPublicKeys = (params: { names: string[] }) =>
  http.post<
    {
      content: string;
      description: string;
      name: string;
    }[]
  >('/apis/core/encrypt/fetch_public_keys/', params);

/**
 * 校验密码强度
 */
export const verifyPasswordStrength = (params: { security_type: string; password: string }) =>
  http.post<PasswordStrength>(`${path}/verify_password_strength/`, params);
