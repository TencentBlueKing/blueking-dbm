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
import type { ListBase } from '../types/common';

const path = '/apis/group';

export interface InfluxDBGroupItem {
  id: number,
  creator: string,
  create_at: string,
  updater: string,
  update_at: string,
  bk_biz_id: number,
  instance_count: number,
  name: string
}

/**
 * 分组列表
 */
export const getGroupList = function (params: { bk_biz_id: number }) {
  return http.get<ListBase<InfluxDBGroupItem[]>>(`${path}/`, {
    limit: -1,
    ...params,
  });
};

/**
 * 创建分组
 */
export const createGroup = function (params: {
  bk_biz_id: number,
  name: string
}) {
  return http.post<InfluxDBGroupItem>(`${path}/`, params);
};

/**
 * 获取分组信息
 */
export const getGroupInfo = function (params: { id: number }) {
  return http.get<InfluxDBGroupItem>(`${path}/${params.id}/`);
};

/**
 * 更新分组信息
 */
export const updateGroupInfo = function (params: {
  id: number,
  bk_biz_id: number,
  name: string
}) {
  return http.put<InfluxDBGroupItem>(`${path}/${params.id}/`, params);
};

/**
 * 删除分组
 */
export const deleteGroup = function (params: { id: number }) {
  return http.delete(`${path}/${params.id}/`);
};

/**
 * 移动实例到新分组
 */
export const moveInstancesToGroup = function (params: {
  new_group_id: number,
  instance_ids: number[]
}) {
  return http.post(`${path}/move_instances/`, params);
};
