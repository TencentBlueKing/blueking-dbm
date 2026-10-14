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
 * 一条变更项：提交时确认弹窗展示什么就存什么，详情页的变更对比原样展示，不再按快照重算
 */
export interface TicketModifyChangeItem {
  // 列表字段，展示时逗号连排并默认折叠
  isList: boolean;
  label: string;
  next: string;
  path: string;
  prev: string;
}

/**
 * 单据改单记录，details 为该次修改的改前快照
 */
export default class TicketModifyRecord<T = Record<string, unknown>> {
  static readonly MODE_ADJUST_APPLY = MODE_ADJUST_APPLY;
  static readonly MODE_ON_BEHALF = MODE_ON_BEHALF;
  static readonly MODE_RE_EDIT = MODE_RE_EDIT;

  // 出口词：重新编辑模式提交后的出口统一为「重新提交」（工具页模式名、入口按钮仍叫「重新编辑」）
  static modeTextMap: Record<TicketModifyMode, string> = {
    [MODE_ADJUST_APPLY]: t('调整申请'),
    [MODE_ON_BEHALF]: t('代为修改'),
    [MODE_RE_EDIT]: t('重新提交'),
  };

  change_count: number;
  // 提交时的变更项列表，变更对比直接展示；早于该字段的记录为空
  change_details: TicketModifyChangeItem[];
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
    this.change_details = payload.change_details || [];
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
