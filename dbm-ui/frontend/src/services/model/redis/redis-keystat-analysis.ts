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

export default class RedisKeystatAnalysis {
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

  analysis_time: number;
  analyzed_shard_num: number;
  atime_available: boolean;
  bk_biz_id: number;
  cluster_id: number;
  cluster_shard_num: number;
  cluster_type: string;
  create_at: string;
  creator: string;
  current_progress: string;
  exec_ip: string;
  immute_domain: string;
  keystat_rank_rows_num: number;
  keystat_report_rows_num: number;
  record_id: number;
  redis_version: string;
  root_id: string;
  sampling_ratio: number;
  source_addr_list: {
    addr: string;
  }[];
  source_role: string;
  source_type: string;
  status: string;
  ticket_id: number;
  update_at: string;
  updater: string;

  constructor(payload = {} as RedisKeystatAnalysis) {
    this.analysis_time = payload.analysis_time;
    this.analyzed_shard_num = payload.analyzed_shard_num;
    this.atime_available = payload.atime_available;
    this.bk_biz_id = payload.bk_biz_id;
    this.cluster_id = payload.cluster_id;
    this.cluster_shard_num = payload.cluster_shard_num;
    this.cluster_type = payload.cluster_type;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.current_progress = payload.current_progress;
    this.exec_ip = payload.exec_ip;
    this.immute_domain = payload.immute_domain;
    this.keystat_rank_rows_num = payload.keystat_rank_rows_num;
    this.keystat_report_rows_num = payload.keystat_report_rows_num;
    this.record_id = payload.record_id;
    this.redis_version = payload.redis_version;
    this.root_id = payload.root_id;
    this.sampling_ratio = payload.sampling_ratio;
    this.source_addr_list = payload.source_addr_list;
    this.source_role = payload.source_role;
    this.source_type = payload.source_type;
    this.status = payload.status;
    this.ticket_id = payload.ticket_id;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at) || '--';
  }

  get statusText() {
    return RedisKeystatAnalysis.STATUS_TEXT_MAP[this.status] || '--';
  }

  get statusTheme() {
    return RedisKeystatAnalysis.STATUS_THEME_MAP[this.status] || 'danger';
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at) || '--';
  }
}
