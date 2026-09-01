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
import http, { type IRequestPayload } from '@services/http';
import AlarmEventModel from '@services/model/monitor/alarm-event';
import AlarmShieldModel from '@services/model/monitor/alarm-shield';
import DutyRuleModel from '@services/model/monitor/duty-rule';
import MonitorPolicyModel from '@services/model/monitor/monitor-policy';
import type { ListBase } from '@services/types';

import type { DBTypes } from '@common/const';

interface UpdatePolicyParams {
  agg_info: MonitorPolicyModel['agg_info'];
  custom_conditions: MonitorPolicyModel['custom_conditions'];
  detects_config: MonitorPolicyModel['detects_config'];
  get_data_time?: string;
  is_enabled: boolean;
  no_data_config: MonitorPolicyModel['no_data_config'];
  notify_config: MonitorPolicyModel['notify_config'];
  notify_groups: number[];
  notify_rules: string[];
  policy_tag: MonitorPolicyModel['policy_tag'];
  targets: MonitorPolicyModel['targets'];
  test_rules: MonitorPolicyModel['test_rules'];
}

interface CreateCycleDutyRuleParams {
  category: string;
  db_type: string;
  duty_arranges: {
    duty_day: number;
    duty_number: number;
    members: string[];
    work_days: number[];
    work_times: string[];
    work_type: string;
  }[];
  effective_time: string;
  end_time: string;
  name: string;
  priority: number;
}

interface CreateCustomDutyRuleParams extends Omit<CreateCycleDutyRuleParams, 'duty_arranges'> {
  duty_arranges: {
    date: string;
    members: string[];
    work_times: string[];
  }[];
}

interface AlarmGroupItem {
  bk_biz_id: number;
  db_type: string;
  details: {
    alert_notice: {
      notify_config: {
        level: 3 | 2 | 1;
        notice_ways: {
          name: string;
          receivers?: string[];
        }[];
      }[];
      time_range: string;
    }[];
  };
  group_type: string;
  id: number;
  is_built_in: boolean;
  monitor_group_id: number;
  name: string;
  receivers: {
    id: string;
    type: string;
  }[];
  related_policy_count: number;
  update_at: string;
  updater: string;
}

const path = '/apis/monitor';

// 获取策略列表
export const queryMonitorPolicyList = (
  params: {
    bk_biz_id?: number;
    db_type?: string;
    id?: number;
    limit?: number;
    name?: string;
    notify_groups?: string;
    offset?: number;
    target_keyword?: string; // 监控目标
    updater?: string;
  },
  payload = {} as IRequestPayload,
) =>
  http.get<ListBase<MonitorPolicyModel[]>>(`${path}/policy/`, params, payload).then((data) => ({
    ...data,
    results: data.results.map(
      (item) =>
        new MonitorPolicyModel(
          Object.assign(item, {
            permission: Object.assign({}, item.permission, data.permission),
          }),
        ),
    ),
  }));

// 更新策略
export const updatePolicy = (id: number, params: { name?: string } & UpdatePolicyParams) =>
  http.post<{
    bkm_id: number;
    local_id: number;
  }>(`${path}/policy/${id}/update_strategy/`, params);

// 批量更新策略告警组
export const batchUpdateNotifyGroup = (params: {
  bk_biz_id: number;
  notify_groups: {
    groups: number[];
    policy_id: number;
  }[];
  voice_notice?: string;
}) => http.post(`/apis/monitor/policy/batch_update_notify_group/`, params);

// 克隆策略
export const clonePolicy = (
  params: {
    bk_biz_id: number;
    name: string;
    parent_id: number;
  } & UpdatePolicyParams,
) =>
  http.post<{
    bkm_id: number;
    local_id: number;
  }>(`${path}/policy/clone_strategy/`, params);

// 启用策略
export const enablePolicy = (params: { id: number }) => http.post<boolean>(`${path}/policy/${params.id}/enable/`);

// 停用策略
export const disablePolicy = (params: { get_data_time?: string; id: number }) =>
  http.post<boolean>(`${path}/policy/${params.id}/disable/`);

// 恢复默认策略
export const resetPolicy = (params: { id: number }) => http.post<void>(`${path}/policy/${params.id}/reset`);

// 删除策略
export const deletePolicy = (params: { id: number }) =>
  http.delete<null | Record<string, any>>(`${path}/policy/${params.id}/`);

// 批量删除策略
export const patchDeletePolicy = (params: { ids: number[] }) => http.post(`${path}/policy/patch_destroy/`, params);

// 根据db类型查询集群列表
export const getClusterList = (params: { bk_biz_id: number; dbtype?: string }) =>
  http.get<string[]>(`${path}/policy/cluster_list/`, params);

// 根据db类型查询模块列表
export const getDbModuleList = (params: { bk_biz_id: number; dbtype?: string }) =>
  http.get<
    {
      db_module_id: number;
      db_module_name: string;
    }[]
  >(`${path}/policy/db_module_list/`, params);

// 根据db类型查询实例列表
export const getInstanceList = (params: { bk_biz_id: number; dbtype?: string }) =>
  http.get<string[]>(`${path}/policy/instance_list/`, params);

// 根据db类型查询ip列表
export const getIpList = (params: { bk_biz_id: number; dbtype?: string }) =>
  http.get<string[]>(`${path}/policy/ip_list/`, params);

// 根据db类型查询角色列表
export const getRoleList = (params: { bk_biz_id: number; dbtype?: string }) =>
  http.get<string[]>(`${path}/policy/instance_role_list/`, params);

/**
 * 获取告警组列表
 */
export const getAlarmGroupList = (params: { bk_biz_id: number; db_type?: string; limit?: number; offset?: number }) =>
  http.get<ListBase<AlarmGroupItem[]>>(`${path}/notice_group/`, params);

// 查询轮值规则列表
export const queryDutyRuleList = (
  params: { db_type: string; limit: number; offset: number },
  payload = {} as IRequestPayload,
) =>
  http.get<ListBase<DutyRuleModel[]>>(`${path}/duty_rule/`, params, payload).then((data) => ({
    ...data,
    results: data.results.map((item) => new DutyRuleModel(item)),
  }));

// 新建轮值规则
export const createDutyRule = (params: CreateCustomDutyRuleParams | CreateCycleDutyRuleParams) =>
  http.post<DutyRuleModel>(`${path}/duty_rule/`, params);

// 更新轮值规则
export const updateDutyRule = (id: number, params: CreateCustomDutyRuleParams | CreateCycleDutyRuleParams) =>
  http.put<DutyRuleModel>(`${path}/duty_rule/${id}/`, params);

// 部分更新轮值规则
export const updatePartialDutyRule = (
  id: number,
  params: {
    is_enabled?: boolean;
    priority?: number;
  },
) => http.patch<DutyRuleModel>(`${path}/duty_rule/${id}/`, params);

// 删除轮值规则
export const deleteDutyRule = (params: { id: number }) => http.delete<void>(`${path}/duty_rule/${params.id}/`);

// 查询轮值优先级列表
export const getPriorityDistinct = () => http.get<number[]>(`${path}/duty_rule/priority_distinct/`);

interface DutyNoticeConfig {
  after: number;
  channels: Record<string, boolean | string>;
  cron: {
    day_of_month: string;
    day_of_week: string;
    hour: string;
    minute: string;
  };
  enabled: boolean;
}

export const getDutyNoticeConfig = () =>
  http.get<{
    [dbType: string]: DutyNoticeConfig;
  }>(`${path}/duty_rule/duty_notice_config/`);

// 更新轮值排班表
export const updateDutyNoticeConfig = (params: { db_type: DBTypes } & DutyNoticeConfig) =>
  http.post(`${path}/duty_rule/update_duty_notice_config/`, params);

// 立即发送轮值排班表
export const sendDutyNoticeSchedule = (params: { db_type: DBTypes }) =>
  http.post(`${path}/duty_rule/send_duty_notice_schedule/`, params);

// 新增告警屏蔽
export const createAlarmShield = (params: {
  begin_time: string;
  bk_biz_id: number;
  category: string;
  description: string;
  dimension_config: {
    dimension_conditions: {
      condition: string;
      key: string;
      method: string;
      name: string;
      value: string[];
    }[];
    id?: number[];
    level?: number[];
  };
  end_time: string;
}) => http.post<{ id: number }>(`${path}/alarm_shield/`, params);

// 编辑告警屏蔽
export const EditAlarmShield = (params: {
  begin_time: string;
  bk_biz_id: number;
  category: string;
  description: string;
  dimension_config: {
    dimension_conditions: {
      condition: string;
      key: string;
      method: string;
      name: string;
      value: string[];
    }[];
    id?: number[];
    level?: number[];
  };
  end_time: string;
  id: number;
}) => http.put<{ id: number }>(`${path}/alarm_shield/${params.id}/`, params);

// 获取告警屏蔽列表
export const getAlarmShieldList = (params: {
  bk_biz_id: number;
  category?: string;
  conditions?: string;
  is_active?: boolean;
  limit?: number;
  offset?: number;
  time_range__gte?: string;
  time_range__lte?: string;
}) =>
  http
    .get<{
      count: number;
      permission: {
        // alert_shield_create: boolean;
        alert_shield_manage: boolean;
      };
      shield_list: AlarmShieldModel[];
    }>(`${path}/alarm_shield/`, params)
    .then((data) => ({
      count: data.count,
      results: data.shield_list.map(
        (item) =>
          new AlarmShieldModel(
            Object.assign(item, {
              permission: data.permission,
            }),
          ),
      ),
    }));

// 获取告警屏蔽列表
export const getAlarmShieldDetails = (params: { id: number }) =>
  http.get<AlarmShieldModel>(`${path}/alarm_shield/${params.id}/`);

// 解除告警屏蔽
export const disabledAlarmShield = (params: { id: number }) =>
  http.post<null>(`${path}/alarm_shield/${params.id}/disable/`);

/**
 * 获取告警事件列表
 */
export const getAlarmEventsList = (
  params: {
    bk_biz_id?: number;
    db_type?: string;
    end_time: string;
    limit?: number;
    offset?: number;
    self_assist?: boolean;
    self_manage?: boolean;
    severity?: number; // 1 | 2 | 3
    stage?: string; // is_handled | is_ack | is_shielded | is_blocked
    start_time: string;
    status?: string; // ABNORMAL | RECOVERED |  CLOSE
  },
  payload = {} as IRequestPayload,
) =>
  http
    .post<{
      aggs: {
        children: {
          count: number;
          id: number;
          name: string;
        }[];
        count: number;
        id: string;
        name: string;
      }[];
      alerts: AlarmEventModel[];
      overview: {
        children?: {
          count: number;
          id: number;
          name: string;
        }[];
        count?: number;
        id?: number;
        name?: string;
      };
      total: number;
    }>(`${path}/event/search/`, params, payload)
    .then((data) => ({
      aggs: data.aggs,
      count: data.total,
      overview: data.overview,
      results: data.alerts.map((item) => new AlarmEventModel(item)),
    }));

// 获取策略列表
export const getPolicyList = (params: {
  bk_biz_id?: number;
  db_type?: string;
  limit?: number;
  monitor_policy_ids?: string;
  name?: string;
  offset?: number;
}) =>
  http.get<
    ListBase<
      {
        db_type: string;
        monitor_policy_id: number;
        name: string;
      }[]
    >
  >(`${path}/policy/`, params);

// 获取策略判断条件的无数据配置
export const searchAlarmStrategy = (params: { monitor_policy_id: number }) =>
  http.get<{
    agg_dimension: string[];
    data_source_list: {
      data_source_label: string;
      data_type_label: string;
    }[];
    metric_list: {
      bk_biz_id: number;
      collect_interval: number;
      data_label: string;
      data_source_label: string;
      data_target: string;
      data_type_label: string;
      default_condition: any[];
      default_dimensions: string[];
      default_trigger_config: {
        check_window: number;
        count: number;
      };
      description: string;
      dimensions: {
        id: string;
        is_dimension: boolean;
        name: string;
        type: string;
      }[];
      disabled: boolean;
      extend_fields: Record<string, any>;
      id: number;
      metric_field: string;
      metric_field_name: string;
      metric_id: string;
      name: string;
      promql_metric: string;
      readable_name: string;
      related_id: string;
      related_name: string;
      remarks: any[];
      result_table_id: string;
      result_table_label: string;
      result_table_label_name: string;
      result_table_name: string;
      time_field: string;
      unit: string;
      use_frequency: number;
    }[];
  }>(`${path}/policy/search_alarm_strategy/`, params);

// 全局策略恢复初始值
export const resetGlobalStrategy = (params: { policy_id: number }) => http.post(`${path}/policy/reset/`, params);
