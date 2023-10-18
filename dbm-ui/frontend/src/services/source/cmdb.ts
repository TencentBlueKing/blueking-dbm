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

import type { BizItem } from '@services/types/common';

import http from '../http';
import type {
  CreateAbbrParams,
  CreateModuleParams,
  CreateModuleResult,
} from '../types/ticket';

const path = '/apis/cmdb';

/**
 * 模块信息
 */
export interface ModuleItem {
  bk_biz_id: number,
  db_module_id: number,
  name: string,
}

/**
 * 业务列表
 */
export const getBizs = () => http.get<BizItem[]>(`${path}/list_bizs/`).then(res => res.map((item: BizItem) => {
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
 * 创建数据库模块
 */
export const createModules = (params: CreateModuleParams & { id: number }) => http.post<CreateModuleResult>(`${path}/${params.id}/create_module/`, params);

interface UserGroup {
  id: string,
  display_name: string,
  logo: string,
  type: string,
  members: string[],
  disabled?: boolean
}

/**
 * 查询 CC 角色对象
 */
export const getUserGroupList = (params: { bk_biz_id: number }) => http.get<UserGroup[]>(`${path}/${params.bk_biz_id}/list_cc_obj_user/`);

/**
 * 业务下的模块列表
 */
export const getModules = (params: {
  bk_biz_id: number,
  cluster_type: string,
}) => http.get<ModuleItem[]>(`${path}/${params.bk_biz_id}/list_modules/`, params);

/**
 * 设置业务英文缩写
 */
export const createAppAbbr = (params: CreateAbbrParams & { id: number }) => http.post<CreateAbbrParams>(`${path}/${params.id}/set_db_app_abbr/`, params);
