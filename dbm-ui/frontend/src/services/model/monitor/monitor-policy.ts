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

export default class MonitorPolicy {
  bk_biz_id: number;  // 所属业务，等于0则属于平台策略
  creator: string;
  create_at: string;
  dispatch_group_id: number;
  db_type: string; // 所属db组件
  event_count: number; // 事件数量，-1代表未知，实际数量应为>=0
  id: number;
  is_enabled: boolean; // 是否启用
  is_synced: boolean;
  is_checked: boolean;
  is_show_tip: boolean;
  monitor_policy_id: number;
  name: string; // 策略名
  notify_rules: string[];
  notify_groups: number[]; // 告警组ID列表
  policy_status: string; // 策略状态：valid(正常)|invalid（异常）
  parent_id: number;
  sync_at: string;
  targets: {
    rule: {
      key: string; // 业务
      value: string[];  // 业务列表
    };
    level: string;  // 业务级
  }[];
  target_level: string;
  target_priority: number;
  target_keyword: string;
  test_rules: { // 检测规则
    type: string; // 暂时只存在这一种（阈值类）
    level: number; // level: 1（致命）、2（预警）、3(提醒)
    // 列表与列表之间是OR的关系, 列表内的元素间是AND的关系
    config: [
      {
        method: string; // gt(大于)|gte(大于等于)|lt|lte|eq(等于)|neq(不等于)
        threshold: number;
      }][];
    unit_prefix: string;  // 单位，比如%，原样返回即可
  }[];
  updater: string;
  update_at: string;

  constructor(payload = {} as MonitorPolicy) {
    this.bk_biz_id = payload.bk_biz_id;
    this.creator = payload.creator;
    this.create_at = payload.create_at;
    this.dispatch_group_id = payload.dispatch_group_id;
    this.db_type = payload.db_type;
    this.event_count = payload.event_count;
    this.id = payload.id;
    this.is_enabled = payload.is_enabled;
    this.is_synced = payload.is_synced;
    this.is_checked = false;
    this.is_show_tip = false;
    this.monitor_policy_id = payload.monitor_policy_id;
    this.name = payload.name;
    this.notify_rules = payload.notify_rules;
    this.notify_groups = payload.notify_groups;
    this.policy_status = payload.policy_status;
    this.parent_id = payload.parent_id;
    this.sync_at = payload.sync_at;
    this.targets = payload.targets;
    this.target_level = payload.target_level;
    this.target_priority = payload.target_priority;
    this.target_keyword = payload.target_keyword;
    this.test_rules = payload.test_rules;
    this.updater = payload.updater;
    this.update_at = payload.update_at;
  }
}
