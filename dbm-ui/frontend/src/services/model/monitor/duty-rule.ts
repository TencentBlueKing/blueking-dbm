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

export interface DutyCycleItem {
  members: string[];
  duty_day: number;
  work_days: number[];
  work_type: string;
  work_times: string[];
  duty_number: number;
}

export interface DutyCustomItem {
  date: string;
  members: string[];
  work_times: string[];
}

export default class DutyRule {
  category: string;
  creator: string;
  create_at: string;
  db_type: string;
  duty_arranges: DutyCycleItem[] | DutyCustomItem[];
  effective_time: string;
  end_time: string;
  id: number;
  is_enabled: boolean;
  is_show_edit: boolean;
  name: string;
  priority: number;
  status: string;
  updater: string;
  update_at: string;

  constructor(payload = {} as DutyRule) {
    this.id = payload.id;
    this.creator = payload.creator;
    this.create_at = payload.create_at;
    this.category = payload.category;
    this.db_type = payload.db_type;
    this.duty_arranges = payload.duty_arranges;
    this.effective_time = payload.effective_time;
    this.is_enabled = payload.is_enabled;
    this.is_show_edit = false;
    this.end_time = payload.end_time;
    this.name = payload.name;
    this.priority = payload.priority;
    this.updater = payload.updater;
    this.update_at = payload.update_at;
    this.status = this.generateStatus();
  }

  get isNewCreated() {
    return dayjs().isBefore(dayjs(this.create_at).add(24, 'hour'));
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at);
  }

  get effectiveTimeDisplay() {
    return utcDisplayTime(this.effective_time);
  }

  generateStatus() {
    if (!this.is_enabled) {
      return 'TERMINATED'; // 已停用
    }
    const today = dayjs(new Date());
    const startDate = dayjs(this.effective_time);
    const endDate = dayjs(this.end_time);
    if ((today.isSame(startDate) || today.isAfter(startDate)) && today.isBefore(endDate)) {
      return 'ACTIVE'; // 当前生效
    }
    if (today.isBefore(startDate)) {
      return 'NOT_ACTIVE'; // 未生效
    }
    if (today.isAfter(endDate)) {
      return 'EXPIRED'; // 已失效
    }
    return 'EXPIRED'; // 已失效
  }
}
