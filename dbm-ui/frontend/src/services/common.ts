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

import pinyin from 'tiny-pinyin';

import http from './http';
import type {
  BizItem,
  GetModulesParams,
  GetUsesParams,
  IAMParams,
  ModuleItem,
  Permission,
  ProfileItem,
  ProfileResult,
  RelatedSystemUrls,
  UseItem,
} from './types/common';

/**
 * 获取业务列表
 */
export const getBizs = () => http.get<BizItem[]>('/apis/cmdb/list_bizs/').then(res => res.map((item: BizItem) => {
  const biz = { ...item };
  biz.display_name = `[${item.bk_biz_id}] ${item.name}`;
  const parseName = pinyin.parse(item.name);
  const names = [];
  const heads = [];
  for (const word of parseName) {
    const {
      type,
      target,
    } = word;
    names.push(target);
    heads.push(type === 2 ? target[0] : target);
  }
  biz.pinyin_head = heads.join('');
  biz.pinyin_name = names.join('');

  return biz;
}));

/**
 * 获取模型列表
 */
export const getModules = (params: GetModulesParams): Promise<ModuleItem[]> => {
  const { cluster_type } = params;
  return http.get(`/apis/cmdb/${params.bk_biz_id}/list_modules/`, { cluster_type });
};

/**
 * 获取人员列表
 */
export const getUseList = (params: GetUsesParams): Promise<{ count: number, results: UseItem[] }> => http.get('/apis/users/list_users/', params);

/**
 * 个人配置列表
 */
export const getProfile = (): Promise<ProfileResult> => http.get('/apis/conf/profile/get_profile/');

/**
 * 更新个人配置列表
 */
export const upsertProfile = (params: ProfileItem) => http.post('/apis/conf/profile/upsert_profile/', params);

/**
 * 查询系统环境变量
 */
export const getSystemEnviron = () => http.get<Record<string, string>>('/apis/conf/system_settings/environ/');

/**
 * 退出登录
 */
export const getLotout = () => http.get('/logout/');

/**
 * 获取权限申请数据链接
 */
export const getApplyDataLink = (params: IAMParams): Promise<Permission> => http.post('/apis/iam/get_apply_data/', params);

/**
 * 检查当前用户对该动作是否有权限
 */
export const checkAuthAllowed = (params: IAMParams) => http.post<{ action_id: string, is_allowed: boolean }[]>('/apis/iam/check_allowed/', params);

/**
 * 获取监控警告管理地址
 */
export const getMonitorUrl = (params: Record<string, any> & { cluster_type: string, cluster_id?: number, instance_id?: number, }): Promise<{ url: string }> => http.get('/apis/monitor/grafana/get_dashboard/', params);

/**
 * 获取项目版本
 */
export const getProjectVersion = (): Promise<{
  app_version: string,
  chart_version: string,
  version: string,
}> => http.get('/version/');
