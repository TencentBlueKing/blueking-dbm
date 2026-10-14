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

import { utcDisplayTime } from '@utils';

import { t } from '@locales/index';

const MODE_ON_BEHALF = 'ON_BEHALF';
const MODE_RE_EDIT = 'RE_EDIT';
const MODE_ADJUST_APPLY = 'ADJUST_APPLY';

export type TicketModifyMode = typeof MODE_ON_BEHALF | typeof MODE_RE_EDIT | typeof MODE_ADJUST_APPLY;

/**
 * 单据改单记录，details 为该次修改的改前快照
 */
export default class TicketModifyRecord<T = Record<string, unknown>> {
  static readonly MODE_ADJUST_APPLY = MODE_ADJUST_APPLY;
  static readonly MODE_ON_BEHALF = MODE_ON_BEHALF;
  static readonly MODE_RE_EDIT = MODE_RE_EDIT;

  static modeTextMap: Record<TicketModifyMode, string> = {
    [MODE_ADJUST_APPLY]: t('调整申请'),
    [MODE_ON_BEHALF]: t('代为修改'),
    [MODE_RE_EDIT]: t('重新编辑'),
  };

  change_count: number;
  create_at: string;
  details: T;
  flow_id: number;
  id: number;
  mode: TicketModifyMode;
  mode_display: string;
  operator: string;
  remark: string;
  ticket_id: number;

  constructor(payload = {} as TicketModifyRecord<T>) {
    this.change_count = payload.change_count;
    this.create_at = payload.create_at;
    this.details = payload.details;
    this.flow_id = payload.flow_id;
    this.id = payload.id;
    this.mode = payload.mode;
    this.mode_display = payload.mode_display;
    this.operator = payload.operator;
    this.remark = payload.remark || '';
    this.ticket_id = payload.ticket_id;
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }

  get modeText() {
    return TicketModifyRecord.modeTextMap[this.mode];
  }
}
