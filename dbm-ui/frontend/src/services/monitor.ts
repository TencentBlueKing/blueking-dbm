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
import DutyRuleModel from '@services/model/monitor/duty-rule';
import MonitorPolicyModel from '@services/model/monitor/monitor-policy';

import type { ListBase } from './types/common';

interface UpdatePolicyParams {
  custom_conditions: {
    condition: string,
    dimension_name: string,
    key: string,
    method: string,
    value: string[],
  }[];
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

interface CreateCycleDutyRuleParams {
  name: string,
  priority: number,
  db_type: string,
  category: string,
  effective_time: string,
  end_time: string,
  duty_arranges: {
    duty_number: number,
    duty_day: number,
    members: string[],
    work_type: string,
    work_days: number[],
    work_times: string[],
  }[]
}

interface CreateCustomDutyRuleParams extends Omit<CreateCycleDutyRuleParams, 'duty_arranges'> {
  duty_arranges: {
    date: string,
    work_times: string[],
    members: string[],
  }[]
}

interface DutyNoticeConfig {
  person_duty: {
    enable: boolean,
    send_at: {
      num: number,
      unit: string,
    },
  },
  schedule_table: {
    enable: boolean,
    qywx_id: string,
    send_at: {
      freq: string,
      time: string,
      freq_values: number[],
    },
    send_day: number,
  },
}

interface AlarmGroupItem {
  id: number,
  name: string,
  updater: string,
  update_at: string,
  bk_biz_id: number,
  monitor_group_id: number,
  related_policy_count: number,
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
        }[],
        level: 3 | 2 | 1
      }[]
    }[],
  },
  is_built_in: boolean
}

// 获取策略列表
export const queryMonitorPolicyList = (params: {
  bk_biz_id?: number,
  db_type?: string,
  name?: string,
  updater?: string,
  target_keyword?: string, // 监控目标
  notify_groups?: string,
  limit?: number,
  offset?: number,
}) => http.get<ListBase<MonitorPolicyModel[]>>('/apis/monitor/policy/', params).then(data => ({
  ...data,
  results: data.results.map(item => new MonitorPolicyModel(item)),
}));

// 更新策略
export const updatePolicy = (id: number, params: UpdatePolicyParams) => http.post<{
  bkm_id: number,
  local_id: number,
}>(`/apis/monitor/policy/${id}/update_strategy/`, params);

// 克隆策略
export const clonePolicy = (params: UpdatePolicyParams & {
  name: string,
  bk_biz_id: number,
  parent_id: number
}) => http.post<{
  bkm_id: number,
  local_id: number,
}>('/apis/monitor/policy/clone_strategy/', params);

// 启用策略
export const enablePolicy = (params: { id: number }) => http.post<boolean>(`/apis/monitor/policy/${params.id}/enable/`);

// 停用策略
export const disablePolicy = (params: { id: number }) => http.post<boolean>(`/apis/monitor/policy/${params.id}/disable/`);

// 恢复默认策略
export const resetPolicy = (params: { id: number }) => http.post<void>(`/apis/monitor/policy/${params.id}/reset`);

// 删除策略
export const deletePolicy = (params: { id: number }) => http.delete<null | Record<string, any>>(`/apis/monitor/policy/${params.id}/`);

// 根据db类型查询集群列表
export const getClusterList = (params: { dbtype: string }) => http.get<string[]>('/apis/monitor/policy/cluster_list/', params);

// 根据db类型查询模块列表
export const getDbModuleList = (params: { dbtype: string }) => http.get<{
  db_module_id: number,
  db_module_name: string,
}[]>('/apis/monitor/policy/db_module_list/', params);

/**
 * 获取告警组列表
 */
export const getAlarmGroupList = (params: {
  bk_biz_id: number,
  db_type?: string,
  offset?: number,
  limit?: number,
}) => http.get<ListBase<AlarmGroupItem[]>>('/apis/monitor/notice_group/', params);

// 查询轮值规则列表
export const queryDutyRuleList = (params: {
  db_type: string,
  limit: number,
  offset: number,
}) => http.get<ListBase<DutyRuleModel[]>>('/apis/monitor/duty_rule/', params).then(data => ({
  ...data,
  results: data.results.map(item => new DutyRuleModel(item)),
}));

// 新建轮值规则
export const createDutyRule = (params: CreateCustomDutyRuleParams | CreateCycleDutyRuleParams) => http.post<DutyRuleModel>('/apis/monitor/duty_rule/', params);

// 更新轮值规则
export const updateDutyRule = (id: number, params: CreateCustomDutyRuleParams | CreateCycleDutyRuleParams) => http.put<DutyRuleModel>(`/apis/monitor/duty_rule/${id}/`, params);

// 部分更新轮值规则
export const updatePartialDutyRule = (id: number, params: {
  is_enabled?: boolean,
  priority?: number,
}) => http.patch<DutyRuleModel>(`/apis/monitor/duty_rule/${id}/`, params);

// 删除轮值规则
export const deleteDutyRule = (params: { id: number }) => http.delete<void>(`/apis/monitor/duty_rule/${params.id}/`);

// 查询轮值通知配置
export const getDutyNoticeConfig = () => http.get<DutyNoticeConfig>('/apis/conf/system_settings/duty_notice_config/');

// 更新轮值通知配置
export const updateDutyNoticeConfig = (params: DutyNoticeConfig) => http.post<DutyNoticeConfig>('/apis/conf/system_settings/update_duty_notice_config/', params);

// 查询轮值优先级列表
export const getPriorityDistinct = () => http.get<number[]>('/apis/monitor/duty_rule/priority_distinct/');
