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

import type { ListBase } from '@/services/types/common';

// 告警组列表项
interface AlarmGroup {
  id: number,
  name: string,
  updater: string,
  update_at: string,
  bk_biz_id: number,
  monitor_group_id: number,
  related_policy_count: number,
  group_type: string,
  db_type: string,
  receivers: AlarmGroupRecivers[],
  details: AlarmGroupDetail
  is_built_in: boolean
}

// 告警组列表通知对象
interface AlarmGroupRecivers {
  type: string,
  id: string
}

// 告警组详情
interface AlarmGroupDetail {
  alert_notice: {
    time_range: string,
    notify_config: {
      notice_ways: {
        name: string,
        receivers?: string[]
      } [],
      level: 3 | 2 | 1
    }[]
  }[]
}

// 告警组新增、编辑参数
interface AlarmGroupDetailParams {
  bk_biz_id: number
  name: string,
  receivers: AlarmGroupRecivers[],
  details: AlarmGroupDetail
  id?: number
}

// 告警组用户组
interface UserGroup {
  id: string,
  display_name: string,
  logo: string,
  type: string,
  members: string[],
  disabled?: boolean
}

// 告警组通知方式
interface AlarmGroupNotify {
  type: string,
  label: string,
  is_active: boolean,
  icon: string
}

/**
 * 获取告警组列表
 */
export const getAlarmGroupList = (params: {
  bk_biz_id: number,
  name: string,
  limit: number,
  offset: number
}) => http.get<ListBase<AlarmGroup[]>>('/apis/monitor/notice_group/', params);

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
export const getUserGroupList = (bizId: number) => http.get<UserGroup[]>(`/apis/cmdb/${bizId}/list_cc_obj_user/`);

/**
 * 获取告警组通知方式
 */
export const getAlarmGroupNotifyList = (params: {
  bk_biz_id: number,
  name?: string,
  limit?: number,
  offset?: number
}) => http.get<AlarmGroupNotify[]>('/apis/monitor/notice_group/get_msg_type/', params);
