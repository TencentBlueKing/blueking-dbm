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

export interface UpdatePolicyParams {
  targets: {
    level: string,
    rule: {
      key: string,
      value: string[],
    },
  }[],
  test_rules: {
    type: string,
    level: number,
    config: [
      {
        method: string,
        threshold: number,
      },
    ][],
    unit_prefix: string,
  }[],
  notify_rules: string[],
  notify_groups: number[],
}


// 告警组列表项
export interface AlarmGroupItem {
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
export interface AlarmGroupRecivers {
  type: string,
  id: string
}

// 告警组详情
export interface AlarmGroupDetail {
  alert_notice: AlarmGroupNotice[]
}

// 告警组新增、编辑参数
export interface AlarmGroupDetailParams {
  bk_biz_id: number
  name: string,
  receivers: AlarmGroupRecivers[],
  details: AlarmGroupDetail
  id?: number
}

// 告警组通知项
export interface AlarmGroupNotice {
  time_range: string,
  notify_config: {
    notice_ways: {
      name: string,
      receivers?: string[]
    }[],
    level: 3 | 2 | 1
  }[]
}

// 告警组用户组
export interface AlarmGroupUserGroup {
  id: string,
  display_name: string,
  logo: string,
  type: string,
  members: string[],
  disabled?: boolean
}

// 告警组通知方式
export interface AlarmGroupNotify {
  type: string,
  label: string,
  is_active: boolean,
  icon: string
}
