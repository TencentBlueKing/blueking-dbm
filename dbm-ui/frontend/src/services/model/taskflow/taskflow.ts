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
import type { TicketTypesStrings } from '@common/const';

import { utcDisplayTime } from '@utils';

export default class TaskFlow {
  static STATUS_TEXT_MAP: Record<string, string> = {
    CREATED: '等待执行',
    READY: '等待执行',
    RUNNING: '执行中',
    SUSPENDED: '执行中',
    BLOCKED: '执行中',
    FINISHED: '执行成功',
    FAILED: '执行失败',
    REVOKED: '已终止',
  };

  static STATUS_THEME_MAP: Record<string, string> = {
    RUNNING: 'loading',
    SUSPENDED: 'loading',
    BLOCKED: 'loading',
    CREATED: 'default',
    READY: 'default',
    FINISHED: 'success',
  };

  cost_time: number;
  created_at: string;
  created_by: string;
  permission: {
    flow_detail: boolean;
  };
  root_id: string;
  status: string;
  ticket_type: TicketTypesStrings;
  ticket_type_display: string;
  uid: string;
  updated_at: string;

  constructor(payload = {} as TaskFlow) {
    this.cost_time = payload.cost_time;
    this.created_at = payload.created_at;
    this.created_by = payload.created_by;
    this.permission = payload.permission;
    this.root_id = payload.root_id;
    this.status = payload.status;
    this.ticket_type = payload.ticket_type;
    this.ticket_type_display = payload.ticket_type_display;
    this.uid = payload.uid;
    this.updated_at = payload.updated_at;
  }

  get statusText() {
    return TaskFlow.STATUS_TEXT_MAP[this.status] || '--';
  }

  get statusTheme() {
    return TaskFlow.STATUS_THEME_MAP[this.status] || 'danger';
  }

  get createAtDisplay() {
    return utcDisplayTime(this.created_at) || '--';
  }
}
