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

import http from '@services/http';
import type { ListBase } from '@services/types/common';

import type {
  AlarmGroupDetailParams,
  AlarmGroupItem,
  AlarmGroupNotify,
  AlarmGroupUserGroup,
} from './types';

/**
 * 获取告警组列表
 */
export const getAlarmGroupList = (params: {
  bk_biz_id: number,
  name: string,
  limit: number,
  offset: number
}) => http.get<ListBase<AlarmGroupItem[]>>('/apis/monitor/notice_group/', params);

/**
 * 获取告警组关联策略
 */
export const getRelatedPolicy = () => http.get<{
  id: number,
  name: string
}[]>('http://127.0.0.1:8083/mock/11/apis/related_policy');

/**
 * 新建告警组
 */
export const insertAlarmGroup = (params: AlarmGroupDetailParams) => http.post('/apis/monitor/notice_group/', params);

/**
 * 编辑告警组
 */
export const updateAlarmGroup = (params: AlarmGroupDetailParams) => http.put(`/apis/monitor/notice_group/${params.id}/`, params);

/**
 * 删除告警组
 */
export const deleteAlarmGroup = (id: number) => http.delete(`/apis/monitor/notice_group/${id}/`);

/**
 * 获取告警组用户组
 */
export const getUserGroupList = (bizId: number) => http.get<AlarmGroupUserGroup[]>(`/apis/cmdb/${bizId}/list_cc_obj_user/`);

/**
 * 获取告警组通知方式
 */
export const getAlarmGroupNotifyList = (params: {
  bk_biz_id: number,
  name?: string,
  limit?: number,
  offset?: number
}) => http.get<AlarmGroupNotify[]>('/apis/monitor/notice_group/get_msg_type/', params);
