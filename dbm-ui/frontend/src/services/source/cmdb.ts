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

import type { BizItem } from '@services/types';

import http from '../http';

const path = '/apis/cmdb';

/**
 * 业务列表
 */
export function getBizs(params = {} as { action: string }) {
  return http.get<BizItem[]>(`${path}/list_bizs/`, params).then((res) =>
    res.map((item: BizItem) => {
      const biz = { ...item };
      biz.display_name = `[${item.bk_biz_id}] ${item.name}`;
      const parseName = pinyin.parse(item.name);
      const names = [];
      const heads = [];
      for (const word of parseName) {
        const { target, type } = word;
        names.push(target);
        heads.push(type === 2 ? target[0] : target);
      }
      biz.pinyin_head = heads.join('');
      biz.pinyin_name = names.join('');

      return biz;
    }),
  );
}

/**
 * 创建数据库模块
 */
export function createModules(params: {
  alias_name: string;
  biz_id: number;
  cluster_type: string;
  db_module_name: string;
}) {
  return http.post<{
    bk_biz_id: number;
    bk_modules: {
      bk_module_id: string;
      bk_module_name: string;
    }[];
    bk_set_id: number;
    cluster_type: string;
    db_module_id: number;
    db_module_name: string;
    name: string;
  }>(`${path}/${params.biz_id}/create_module/`, params);
}

/**
 * 查询 CC 角色对象
 */
export function getUserGroupList(params: { bk_biz_id: number }) {
  return http.get<
    {
      disabled?: boolean;
      display_name: string;
      id: string;
      logo: string;
      members: string[];
      type: string;
    }[]
  >(`${path}/${params.bk_biz_id}/list_cc_obj_user/`);
}

/**
 * 业务下的模块列表
 */
export function getModules(params: { bk_biz_id: number; cluster_type: string }) {
  return http.get<
    {
      alias_name: string;
      bk_biz_id: number;
      db_module_id: number;
      db_module_info: {
        conf_items: {
          conf_name: string;
          conf_value: string;
          description: string;
          flag_disable: number;
          flag_locked: number;
          level_name: string;
          level_value: string;
          need_restart: number;
          op_type: string;
          stage: number;
          value_allowed: string;
          value_type_sub: string;
        }[];
        description: string;
        name: string;
        updated_at: string;
        updated_by: string;
        version: string;
      };
      name: string;
      permission: {
        dbconfig_view: boolean;
      };
    }[]
  >(`${path}/${params.bk_biz_id}/list_modules/`, params);
}

/**
 * 设置业务英文缩写
 */
export function createAppAbbr(params: { db_app_abbr: string; id: number }) {
  return http.post<{
    db_app_abbr: string;
  }>(`${path}/${params.id}/set_db_app_abbr/`, params);
}

/**
 * 获取当前集群类型所有业务下模型列表
 */
export const getBizModuleTopoTree = (params: {
  bk_biz_name?: string;
  cluster_type: string; // 逗号分隔
  count_type?: string; // 以cluster/instance为维度 统计业务模块对应的数量信息
  limit?: number;
  module_name?: string;
  offset?: number;
  role?: string; // 如果count_type是instance实例   根据过滤条件是传参
}) =>
  http.get<
    {
      bk_biz_id: number;
      bk_biz_name: string;
      count: number;
      modules: {
        count: number;
        module_id: number;
        module_name: string;
      }[];
    }[]
  >(`${path}/list_biz_module_trees/`, params);
