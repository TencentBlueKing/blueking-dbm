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

export default class AlarmShield {
  begin_time: string;
  bk_biz_id: number;
  category: string;
  content: string;
  cycle_config: {
    begin_time: string;
    day_list: string[];
    end_time: string;
    type: number;
    week_list: string[];
  };
  description: string;
  dimension_config: {
    _alert_id?: string;
    _alert_message?: string;
    _dimensions?: string;
    _severity?: number;
    bk_cloud_id?: number;
    bk_target_ip?: {
      bk_host_id: number;
      bk_target_cloud_id: number;
      bk_target_ip: string;
    }[];
    dimension_conditions: {
      condition: string;
      key: string;
      method: string;
      name: string;
      value: string[];
    }[];
    ip?: string;
    level: number[];
    strategy_id: number[] | number;
    'tags.app'?: string;
    'tags.appid'?: string;
    'tags.cluster_domain'?: string;
    'tags.instance_role'?: string;
  };
  end_time: string;
  failure_time: string;
  id: number;
  is_enabled: boolean;
  notice_config: string;
  permission: {
    alert_shield_create: boolean;
    alert_shield_manage: boolean;
  };
  shield_notice: boolean;
  source: string;
  status: number;
  update_user: string;

  constructor(payload = {} as AlarmShield) {
    this.begin_time = payload.begin_time;
    this.bk_biz_id = payload.bk_biz_id;
    this.category = payload.category;
    this.content = payload.content || '--';
    this.cycle_config = payload.cycle_config;
    this.description = payload.description;
    this.dimension_config = payload.dimension_config;
    this.end_time = payload.end_time;
    this.failure_time = payload.failure_time;
    this.id = payload.id;
    this.is_enabled = payload.is_enabled;
    this.notice_config = payload.notice_config;
    this.permission = payload.permission;
    this.shield_notice = payload.shield_notice;
    this.source = payload.source;
    this.status = payload.status;
    this.update_user = payload.update_user;
  }

  get isEdiatable() {
    return ['dimension', 'strategy'].includes(this.category);
  }

  get shieldTimeDisplay() {
    if (this.begin_time && this.end_time) {
      const beginTime = dayjs(this.begin_time);
      const endTime = dayjs(this.end_time);
      const duration = dayjs.duration(endTime.diff(beginTime));
      const days = Math.floor(duration.asDays());
      return `${days}${t('天')} ( ${utcDisplayTime(this.begin_time)} ~ ${utcDisplayTime(this.end_time)} )`;
    }
    return '--';
  }

  get statusDisplay() {
    if (this.status === 2) {
      return t('已过期');
    }

    return t('被解除');
  }
}
