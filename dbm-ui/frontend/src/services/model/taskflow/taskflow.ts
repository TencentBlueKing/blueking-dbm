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

  root_id: string;
  ticket_type_display: string;
  ticket_type: TicketTypesStrings;
  status: string;
  uid: string;
  created_by: string;
  created_at: string;
  cost_time: number;
  bk_biz_id: number;
  bk_host_ids?: number[];

  constructor(payload = {} as TaskFlow) {
    this.root_id = payload.root_id;
    this.ticket_type_display = payload.ticket_type_display;
    this.ticket_type = payload.ticket_type;
    this.status = payload.status;
    this.uid = payload.uid;
    this.created_by = payload.created_by;
    this.created_at = payload.created_at;
    this.cost_time = payload.cost_time;
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_host_ids = payload.bk_host_ids || [];
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
