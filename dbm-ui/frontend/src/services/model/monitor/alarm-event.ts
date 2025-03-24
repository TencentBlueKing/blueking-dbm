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

import { utcDisplayTime } from '@utils';

import { t } from '@locales/index';

type DimensionInfo = AlarmEvent['dimensions'][number] | undefined;

export default class AlarmEvent {
  ack_duration: number;
  ack_operator: string;
  alert_name: string;
  appointee: string[];
  assignee: string[];
  begin_time: number;
  bk_biz_id: number;
  bk_biz_name: string;
  bk_cloud_id: number;
  bk_host_id: number;
  bk_service_instance_id: string;
  bk_topo_node: string[];
  category: string;
  category_display: string;
  converage_id: string;
  create_time: number;
  data_type: string;
  dbm_event: boolean;
  dedupe_keys: string[];
  dedupe_md5: string;
  description: string;
  dimension_message: string;
  dimensions: {
    display_key: string;
    display_value: string;
    key: string;
    value: string;
  }[];
  duration: string;
  end_time: number;
  event_id: string;
  first_anomaly_time: number;
  follower: string;
  id: string;
  ip: string;
  ipv6: string;
  is_ack: boolean;
  is_blocked: boolean;
  is_handled: boolean;
  is_shielded: boolean;
  labels: string[];
  latest_time: number;
  metric: string[];
  metric_display: {
    id: string;
    name: string;
  }[];
  permission: {
    alert_shield_create: boolean;
  };
  plugin_display_name: string;
  plugin_id: string;
  seq_id: number;
  severity: number;
  shield_id: number[];
  shield_left_time: string;
  stage_display: string;
  status: string;
  strategy_id: number;
  strategy_name: string;
  supervisor: string;
  tags: {
    key: string;
    value: string;
  }[];
  target: string;
  target_key: string;
  target_type: string;
  update_time: number;

  constructor(payload = {} as AlarmEvent) {
    this.ack_duration = payload.ack_duration;
    this.ack_operator = payload.ack_operator;
    this.alert_name = payload.alert_name;
    this.assignee = payload.assignee;
    this.appointee = payload.appointee;
    this.begin_time = payload.begin_time;
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_host_id = payload.bk_host_id;
    this.bk_service_instance_id = payload.bk_service_instance_id;
    this.bk_topo_node = payload.bk_topo_node;
    this.category = payload.category;
    this.category_display = payload.category_display;
    this.converage_id = payload.converage_id;
    this.create_time = payload.create_time;
    this.data_type = payload.data_type;
    this.dbm_event = payload.dbm_event;
    this.dedupe_keys = payload.dedupe_keys;
    this.dedupe_md5 = payload.dedupe_md5;
    this.description = payload.description;
    this.dimension_message = payload.dimension_message;
    this.dimensions = payload.dimensions;
    this.duration = payload.duration;
    this.end_time = payload.end_time;
    this.event_id = payload.event_id;
    this.first_anomaly_time = payload.first_anomaly_time;
    this.follower = payload.follower;
    this.id = payload.id;
    this.ip = payload.ip;
    this.ipv6 = payload.ipv6;
    this.is_ack = payload.is_ack;
    this.is_blocked = payload.is_blocked;
    this.is_handled = payload.is_handled;
    this.is_shielded = payload.is_shielded;
    this.labels = payload.labels;
    this.latest_time = payload.latest_time;
    this.metric = payload.metric;
    this.metric_display = payload.metric_display;
    this.permission = payload.permission;
    this.plugin_display_name = payload.plugin_display_name;
    this.plugin_id = payload.plugin_id;
    this.stage_display = payload.stage_display;
    this.seq_id = payload.seq_id;
    this.shield_id = payload.shield_id;
    this.shield_left_time = payload.shield_left_time;
    this.status = payload.status;
    this.strategy_id = payload.strategy_id;
    this.strategy_name = payload.strategy_name;
    this.severity = payload.severity;
    this.supervisor = payload.supervisor;
    this.tags = payload.tags;
    this.target = payload.target;
    this.target_key = payload.target_key;
    this.target_type = payload.target_type;
    this.update_time = payload.update_time;
  }

  get alarmBizId() {
    const bizTag = this.tags.find((item) => item.key === 'appid');
    if (bizTag) {
      return Number(bizTag.value);
    }

    return undefined;
  }

  get cluster() {
    const clusterInfo = this.dimensions.find((item) => item.key === 'tags.cluster_domain');
    return clusterInfo?.value || '--';
  }

  get createTimeDisplay() {
    return utcDisplayTime(dayjs(this.create_time * 1000).format('YYYY-MM-DD HH:mm:ss'));
  }

  get firstAnomalyTimeDisplay() {
    return utcDisplayTime(dayjs(this.first_anomaly_time * 1000).format('YYYY-MM-DD HH:mm:ss'));
  }

  get instance() {
    let instanceInfo: DimensionInfo;
    let ipInfo: DimensionInfo;
    let hostInfo: DimensionInfo;
    let portInfo: DimensionInfo;
    this.dimensions.forEach((item) => {
      if (item.key === 'instance') {
        instanceInfo = item;
      } else if (item.key === 'ip') {
        ipInfo = item;
      } else if (item.key === 'tags.instance_host') {
        hostInfo = item;
      } else if (item.key === 'tags.instance_port') {
        portInfo = item;
      }
    });
    if (instanceInfo) {
      return instanceInfo.display_value;
    }

    if (ipInfo) {
      return ipInfo.display_value;
    }

    return portInfo ? `${hostInfo?.display_value || '--'}:${portInfo.display_value}` : hostInfo?.display_value || '--';
  }

  get severityColor() {
    switch (this.severity) {
      case 1:
        return '#EA3636';
      case 2:
        return '#F59500';
      default:
        return '#3A84FF';
    }
  }

  get severityDisplayName() {
    switch (this.severity) {
      case 1:
        return t('致命');
      case 2:
        return t('预警');
      default:
        return t('提醒');
    }
  }

  get statusDisplay() {
    switch (this.status) {
      case 'RECOVERED':
        return t('已恢复');
      case 'ABNORMAL':
        return t('未恢复');
      default:
        return t('已失效');
    }
  }
}
