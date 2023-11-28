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

const path = '/apis/monitor/notice_group';

/**
 * 告警组列表项
 */
interface AlarmGroup {
  id: number,
  name: string,
  create_at: string,
  creator: string,
  updater: string,
  update_at: string,
  bk_biz_id: number,
  monitor_group_id: number,
  used_count: number,
  group_type: string,
  db_type: string,
  receivers: {
    type: string,
    id: string
  }[],
  details: {
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
  is_built_in: boolean
}

/**
 * 获取告警组列表
 */
export function getAlarmGroupList(params: {
  bk_biz_id: number,
  name: string,
  limit: number,
  offset: number
}) {
  return http.get<ListBase<AlarmGroup[]>>(`${path}/`, params);
}

/**
 * 告警组新增、编辑参数
 */
interface AlarmGroupDetailParams {
  bk_biz_id: number
  name: string,
  receivers: AlarmGroup['receivers'][],
  details: AlarmGroup['details']
  id: number
}

/**
 * 新建告警组
 */
export function insertAlarmGroup(params: Omit<AlarmGroupDetailParams, 'id'>) {
  return http.post(`${path}/`, params);
}

/**
 * 编辑告警组
 */
export function updateAlarmGroup(params: AlarmGroupDetailParams) {
  return http.put(`${path}/${params.id}/`, params);
}

/**
 * 删除告警组
 */
export function deleteAlarmGroup(params: { id: number }) {
  return http.delete(`${path}/${params.id}/`);
}

/**
 * 获取告警组通知方式
 */
export function getAlarmGroupNotifyList(params: {
  bk_biz_id: number,
  name?: string,
  limit?: number,
  offset?: number
}) {
  return http.get<{
    type: string,
    label: string,
    is_active: boolean,
    icon: string
  }[]>(`${path}/get_msg_type/`, params);
}
