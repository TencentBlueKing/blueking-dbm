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

import http from '../http';
import type { ListBase } from '../types';

const path = '/apis/group';

/**
 * 分组列表
 */
export function getGroupList(params: { bk_biz_id: number }) {
  return http
    .get<
      ListBase<
        {
          bk_biz_id: number;
          create_at: string;
          creator: string;
          id: number;
          instance_count: number;
          name: string;
          permission: {
            group_manage: boolean;
          };
          update_at: string;
          updater: string;
        }[]
      >
    >(`${path}/`, {
      limit: -1,
      ...params,
    })
    .then((data) => ({
      ...data,
      results: data.results.map((item) =>
        Object.assign(item, {
          permission: data.permission || {},
        }),
      ),
    }));
}

/**
 * 创建分组
 */
export function createGroup(params: { bk_biz_id: number; name: string }) {
  return http.post<{
    id: number;
    creator: string;
    create_at: string;
    updater: string;
    update_at: string;
    bk_biz_id: number;
    instance_count: number;
    name: string;
  }>(`${path}/`, params);
}

/**
 * 获取分组信息
 */
export function getGroupInfo(params: { id: number }) {
  return http.get<{
    id: number;
    creator: string;
    create_at: string;
    updater: string;
    update_at: string;
    bk_biz_id: number;
    instance_count: number;
    name: string;
  }>(`${path}/${params.id}/`);
}

/**
 * 更新分组信息
 */
export function updateGroupInfo(params: { id: number; bk_biz_id: number; name: string }) {
  return http.put<{
    id: number;
    creator: string;
    create_at: string;
    updater: string;
    update_at: string;
    bk_biz_id: number;
    instance_count: number;
    name: string;
  }>(`${path}/${params.id}/`, params);
}

/**
 * 删除分组
 */
export function deleteGroup(params: { id: number }) {
  return http.delete(`${path}/${params.id}/`);
}

/**
 * 移动实例到新分组
 */
export function moveInstancesToGroup(params: { new_group_id: number; instance_ids: number[] }) {
  return http.post(`${path}/move_instances/`, params);
}
