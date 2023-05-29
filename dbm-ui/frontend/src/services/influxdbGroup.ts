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

import http from './http';
import type { ListBase } from './types/common';
import type { InfluxDBGroupItem } from './types/influxdbGroup';

/**
 * 分组列表
 */
export const getGroupList = (params: { bk_biz_id: number }): Promise<ListBase<InfluxDBGroupItem[]>> => http.get('/apis/group/', {
  limit: -1,
  ...params,
});

/**
 * 创建分组
 */
export const createGroup = (params: { bk_biz_id: number, name: string }): Promise<InfluxDBGroupItem> => http.post('/apis/group/', params);

/**
 * 获取分组信息
 */
export const getGroupInfo = (id: number): Promise<InfluxDBGroupItem> => http.get(`/apis/group/${id}/`);

/**
 * 更新分组信息
 */
export const updateGroupInfo = (id: number, params: { bk_biz_id: number, name: string }): Promise<InfluxDBGroupItem> => http.put(`/apis/group/${id}/`, params);

/**
 * 删除分组
 */
export const deleteGroup = (id: number) => http.delete(`/apis/group/${id}/`);

/**
 * 移动实例到新分组
 */
export const moveInstancesToGroup = (params: { new_group_id: number, instance_ids: number[] }) => http.post('/apis/group/move_instances/', params);
