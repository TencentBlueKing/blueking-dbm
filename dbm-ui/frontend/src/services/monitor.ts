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

import type { AlarmGroupItem } from '@views/monitor-alarm-db/alarm-group/common/types';

import type { ListBase } from './types/common';
import type {
  CreateCustomDutyRuleParams,
  CreateCycleDutyRuleParams,
  UpdatePolicyParams,
} from './types/monitor';

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
export const enablePolicy = (id: number) => http.post<boolean>(`/apis/monitor/policy/${id}/enable/`);

// 停用策略
export const disablePolicy = (id: number) => http.post<boolean>(`/apis/monitor/policy/${id}/disable/`);

// 恢复默认策略
export const resetPolicy = (id: number) => http.post<void>(`/apis/monitor/policy/${id}/reset`);

// 删除策略
export const deletePolicy = (id: number) => http.delete<void>(`/apis/monitor/policy/${id}/`);

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
  dbtype: string,
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
export const deleteDutyRule = (id: number) => http.delete<void>(`/apis/monitor/duty_rule/${id}/`);
