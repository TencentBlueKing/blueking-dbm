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

import type {
  AlarmGroupDetailParams,
  AlarmGroupItem,
  AlarmGroupNotify,
  AlarmGroupUserGroup,
} from './types';

import type { ListBase } from '@/services/types/common';
/**
 * 获取告警组列表
 */
export const getList = () => http.get<ListBase<AlarmGroupItem[]>>('http://127.0.0.1:8083/mock/11/apis/monitor/notice_group/');

/**
 * 获取告警组关联策略
 */
export const getRelatedPolicy = () => http.get<{
  id: number,
  name: string
}>('http://127.0.0.1:8083/mock/11/apis/related_policy');

/**
 * 编辑告警组
 */
export const updateAlarmGroup = (params: AlarmGroupDetailParams) => http.put('http://127.0.0.1:8083/mock/11/apis/monitor/notice_group/{id}/', params);

/**
 * 删除告警组
 */
export const deleteAlarmGroup = (id: number) => http.delete(`http://127.0.0.1:8083/mock/11/apis/monitor/notice_group/${id}/`);

/**
 * 获取告警组用户组
 */
export const getUserGroupList = () => http.get<AlarmGroupUserGroup[]>('http://127.0.0.1:8083/mock/11/apis/monitor/user_group_list');

/**
 * 获取告警组通知方式
 */
export const getNotifyList = () => http.get<AlarmGroupNotify[]>('http://127.0.0.1:8083/mock/11/apis/monitor/notify_list');
