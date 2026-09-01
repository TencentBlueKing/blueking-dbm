/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited; a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing; software distributed under the License is distributed
 * on an "AS IS" BASIS; WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND; either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */
import dayjs from 'dayjs';

import type { BizItem } from '@services/types';

import { MonitorTargetLevel } from '@common/const';

import { utcDisplayTime } from '@utils';

import { t } from '@locales/index';

export default class MonitorPolicy {
  static MULTI = 'multi';
  static PROMQL = 'PromQL';
  static SINGLE = 'single';

  static PolicyType = {
    MULTI: MonitorPolicy.MULTI,
    PROMQL: MonitorPolicy.PROMQL,
    SINGLE: MonitorPolicy.SINGLE,
  };

  static PolicyTypeTextMap = {
    [MonitorPolicy.MULTI]: t('多指标'),
    [MonitorPolicy.PROMQL]: 'PromQL',
    [MonitorPolicy.SINGLE]: t('单指标'),
  };

  static PolicyTypeList = Object.values(MonitorPolicy.PolicyType).map((item) => ({
    label: MonitorPolicy.PolicyTypeTextMap[item],
    value: item,
  }));

  /**
   * @param name - 策略名称
   */
  static FormatDisplayName(name: string) {
    const match = name.match(/^DBM#([a-z0-9][a-z0-9-]*) (.+)$/);
    if (match && match[2]) {
      return match[2];
    }
    return;
  }

  /**
   * @param code - 业务英文名或id
   * @param name - 策略名称
   */
  static FormatFinalName(name: string, bizInfo?: BizItem) {
    const code = bizInfo?.english_name || bizInfo?.bk_biz_id || '';
    return `DBM#${code} ${name}`;
  }

  agg_info: {
    agg_interval: number;
    agg_method: string;
    metric_field: string;
    metric_id: string;
    promql: string;
  }[];
  bk_biz_id: number; // 所属业务，等于0则属于平台策略
  child: MonitorPolicy[];
  create_at: string;
  creator: string;
  custom_conditions: {
    condition: string;
    dimension_name: string;
    key: string;
    method: string;
    value: string[];
  }[];
  db_type: string; // 所属db组件
  details: {
    items: {
      expression: string;
      query_configs: {
        data_source_label: string;
      }[];
    }[];
  };
  detects_config: {
    recovery_config: {
      check_window: number;
      status_setter: 'recovery' | 'recovery-nodata' | 'cover';
    };
    trigger_config: {
      check_window: number;
      count: number;
      uptime: {
        active_calendars: string[];
        calendars: string[];
        time_ranges: {
          end: string;
          start: string;
        }[];
      };
    };
  };
  dispatch_group_id: number;
  event_count: number; // 事件数量，-1代表未知，实际数量应为>=0
  event_url: string;
  id: number;
  is_checked: boolean;
  is_enabled: boolean; // 是否启用
  is_synced: boolean;
  monitor_indicator: string;
  monitor_policy_id: number;
  name: string; // 策略名
  no_data_config: {
    agg_dimension: string[];
    continuous: number;
    is_enabled: boolean;
    level: number;
  };
  notify_config: {
    interval_notify_mode: string;
    notify_interval: number; // 单位秒
    voice_notice: string;
  };
  notify_groups: number[]; // 告警组ID列表
  notify_rules: string[];
  parent_id: number;
  permission: {
    global_alarm_policy_manage: boolean;
    monitor_policy_alarm_view: boolean;
    // monitor_policy_clone: boolean;
    // monitor_policy_delete: boolean;
    // monitor_policy_edit: boolean;
    monitor_policy_manage: boolean;
    // monitor_policy_start_stop: boolean;
  };
  policy_status: string; // 策略状态：valid(正常)|invalid（异常）
  policy_tag: 'inner' | 'custom' | 'subord'; // 内置、自定义、子策略
  sync_at: string;
  target_keyword: string;
  target_level: MonitorTargetLevel;
  target_priority: number;
  targets: {
    level: string;
    rule: {
      key: string;
      method: string;
      value: string[];
    };
  }[];
  // 检测规则
  test_rules: {
    // 列表与列表之间是OR的关系, 列表内的元素间是AND的关系
    config: {
      method: string; // gt(大于)|gte(大于等于)|lt|lte|eq(等于)|neq(不等于)
      threshold: number;
    }[][];
    level: number; // level: 1（致命）、2（预警）、3(提醒)
    type: string; // 暂时只存在这一种（阈值类）
    unit_prefix: string; // 单位，比如%，原样返回即可
  }[];
  update_at: string;
  updater: string;

  constructor(payload = {} as MonitorPolicy) {
    this.agg_info = payload.agg_info;
    this.bk_biz_id = payload.bk_biz_id;
    this.creator = payload.creator;
    this.child = payload.child || [];
    this.create_at = payload.create_at;
    this.custom_conditions = payload.custom_conditions;
    this.details = payload.details;
    this.dispatch_group_id = payload.dispatch_group_id;
    this.db_type = payload.db_type;
    this.detects_config = payload.detects_config;
    this.event_count = payload.event_count;
    this.event_url = payload.event_url;
    this.id = payload.id;
    this.is_enabled = payload.is_enabled;
    this.is_synced = payload.is_synced;
    this.is_checked = false;
    this.monitor_policy_id = payload.monitor_policy_id;
    this.monitor_indicator = payload.monitor_indicator;
    this.name = payload.name;
    this.notify_config = payload.notify_config;
    this.no_data_config = payload.no_data_config;
    this.notify_rules = payload.notify_rules;
    this.notify_groups = payload.notify_groups;
    this.policy_status = payload.policy_status;
    this.policy_tag = payload.policy_tag;
    this.parent_id = payload.parent_id;
    this.permission = payload.permission || {};
    this.sync_at = payload.sync_at;
    this.targets = payload.targets;
    this.target_level = payload.target_level;
    this.target_priority = payload.target_priority;
    this.target_keyword = payload.target_keyword;
    this.test_rules = payload.test_rules;
    this.updater = payload.updater;
    this.update_at = payload.update_at;
  }
  get expression() {
    return this.details.items[0].expression;
  }

  get isChild() {
    return (
      ![MonitorTargetLevel.BIZ, MonitorTargetLevel.PLATFORM].includes(this.target_level) && this.policy_tag === 'subord'
    );
  }

  get isCustom() {
    return this.target_level === MonitorTargetLevel.BIZ && this.policy_tag === 'custom';
  }

  get isInnerFake() {
    return this.target_level === MonitorTargetLevel.BIZ && this.policy_tag === 'inner';
  }

  get isInnerReal() {
    return this.target_level === MonitorTargetLevel.PLATFORM && this.policy_tag === 'inner';
  }

  get isNewCreated() {
    return dayjs().isBefore(dayjs(this.create_at).add(24, 'hour'));
  }

  get isPolicyTypeMulti() {
    return this.policyType === MonitorPolicy.MULTI;
  }

  get isPolicyTypePromQL() {
    return this.policyType === MonitorPolicy.PROMQL;
  }

  get nameDisplay() {
    if (!this.isInnerReal) {
      const match = MonitorPolicy.FormatDisplayName(this.name);
      if (match) {
        return match;
      }
    }
    return this.name;
  }

  get policyType() {
    if (this.details.items[0].query_configs[0].data_source_label === 'prometheus') {
      return MonitorPolicy.PROMQL;
    }
    if (this.details.items[0].query_configs.length >= 2) {
      return MonitorPolicy.MULTI;
    }
    return MonitorPolicy.SINGLE;
  }

  get timeRangesDisplay() {
    const timeRanges = this.detects_config.trigger_config.uptime.time_ranges;
    if (timeRanges.length === 0) {
      return;
    }

    const parseTimeToMinutes = (time: string) => {
      if (time === '24:00') {
        return 1440;
      }
      const [hour, minutes] = time.split(':').map(Number);
      return hour * 60 + minutes;
    };

    const calcCoveredMinutes = () => {
      const minutes = Array.from({ length: 24 * 60 }, () => false);
      timeRanges.forEach((range) => {
        const start = parseTimeToMinutes(range.start);
        let end = parseTimeToMinutes(range.end);
        if (range.end === '23:59') {
          end = 1440;
        }
        for (let i = start; i < end; i++) {
          minutes[i] = true;
        }
      });
      return minutes.filter(Boolean).length;
    };

    const totalMinutes = calcCoveredMinutes();
    if (totalMinutes >= 1440) {
      return [];
    }
    return timeRanges.map((item) => `${item.start} - ${item.end}`);
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at);
  }
}
