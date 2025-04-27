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

export default class RedisHotKey {
  static STATUS_TEXT_MAP: Record<string, string> = {
    FAILED: t('执行失败'),
    FINISHED: t('执行成功'),
    READY: t('等待执行'),
    REVOKED: t('已终止'),
    RUNNING: t('执行中'),
  };

  static STATUS_THEME_MAP: Record<string, string> = {
    BLOCKED: 'loading',
    CREATED: 'default',
    FINISHED: 'success',
    READY: 'default',
    RUNNING: 'loading',
    SUSPENDED: 'loading',
  };

  analysis_time: string;
  bk_biz_id: number;
  cluster_id: number;
  cluster_type: string;
  create_at: string;
  creator: string;
  id: number;
  immute_domain: string;
  ins_list: string[];
  root_id: string;
  status: string;
  ticket_id: number;
  update_at: string;
  updater: string;

  constructor(payload = {} as RedisHotKey) {
    this.analysis_time = payload.analysis_time;
    this.bk_biz_id = payload.bk_biz_id;
    this.cluster_type = payload.cluster_type;
    this.root_id = payload.root_id;
    this.status = payload.status;
    this.cluster_id = payload.cluster_id;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.id = payload.id;
    this.immute_domain = payload.immute_domain;
    this.ins_list = payload.ins_list;
    this.ticket_id = payload.ticket_id;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at) || '--';
  }

  get statusText() {
    return RedisHotKey.STATUS_TEXT_MAP[this.status] || '--';
  }

  get statusTheme() {
    return RedisHotKey.STATUS_THEME_MAP[this.status] || 'danger';
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at) || '--';
  }
}
