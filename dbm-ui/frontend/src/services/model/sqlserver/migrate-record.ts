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

const enum STATUS {
  DISCONNECTED = 'disconnected',
  DISCONNECTING = 'disconnecting',
  FULL_FAILED = 'full_failed',
  FULL_ONLINE = 'full_online',
  FULL_SUCCESS = 'full_success',
  INCR_FAILED = 'incr_failed',
  INCR_ONLINE = 'incr_online',
  INCR_SUCCESS = 'incr_success',
  TERMINATED = 'terminated',
  TODO = 'todo',
}

export default class MigrateRecord {
  static STATUS_DISCONNECTED = STATUS.DISCONNECTED;
  static STATUS_DISCONNECTING = STATUS.DISCONNECTING;
  static STATUS_FULL_FAILED = STATUS.FULL_FAILED;
  static STATUS_FULL_ONLINE = STATUS.FULL_ONLINE;
  static STATUS_FULL_SUCCESS = STATUS.FULL_SUCCESS;
  static STATUS_INCR_FAILED = STATUS.INCR_FAILED;
  static STATUS_INCR_ONLINE = STATUS.INCR_ONLINE;
  static STATUS_INCR_SUCCESS = STATUS.INCR_SUCCESS;
  static STATUS_TERMINATED = STATUS.TERMINATED;
  static STATUS_TODO = STATUS.TODO;

  static statusIconMap = {
    [STATUS.DISCONNECTED]: 'sync-failed',
    [STATUS.DISCONNECTING]: 'sync-pending',
    [STATUS.FULL_FAILED]: 'sync-failed',
    [STATUS.FULL_ONLINE]: 'sync-pending',
    [STATUS.FULL_SUCCESS]: 'sync-success',
    [STATUS.INCR_FAILED]: 'sync-failed',
    [STATUS.INCR_ONLINE]: 'sync-pending',
    [STATUS.INCR_SUCCESS]: 'sync-success',
    [STATUS.TERMINATED]: 'sync-waiting-01',
    [STATUS.TODO]: 'sync-default',
  };

  static statusTextMap = {
    [STATUS.DISCONNECTED]: t('已断开'),
    [STATUS.DISCONNECTING]: t('中断中'),
    [STATUS.FULL_FAILED]: t('全量传输失败'),
    [STATUS.FULL_ONLINE]: t('全量传输中'),
    [STATUS.FULL_SUCCESS]: t('全量传输完成'),
    [STATUS.INCR_FAILED]: t('增量传输失败'),
    [STATUS.INCR_ONLINE]: t('增量传输中'),
    [STATUS.INCR_SUCCESS]: t('增量传输完成'),
    [STATUS.TERMINATED]: t('已终止'),
    [STATUS.TODO]: t('待执行'),
  };

  bk_biz_id: number;
  create_at: string;
  creator: string;
  db_list: string[];
  dts_config: {
    db_name: string;
    target_db_name: string;
  }[];
  dts_mode: string;
  id: number;
  ignore_db_list: string[];
  root_id: string;
  source_cluster_domain: string;
  source_cluster_id: number;
  status: (typeof STATUS)[keyof typeof STATUS];
  target_cluster_domain: string;
  target_cluster_id: number;
  ticket_id: number;
  update_at: string;
  updater: string;

  constructor(payload = {} as MigrateRecord) {
    this.bk_biz_id = payload.bk_biz_id;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.db_list = payload.db_list || [];
    this.dts_config = payload.dts_config || [];
    this.dts_mode = payload.dts_mode;
    this.id = payload.id;
    this.ignore_db_list = payload.ignore_db_list || [];
    this.root_id = payload.root_id;
    this.source_cluster_domain = payload.source_cluster_domain;
    this.source_cluster_id = payload.source_cluster_id;
    this.status = payload.status;
    this.target_cluster_domain = payload.target_cluster_domain;
    this.target_cluster_id = payload.target_cluster_id;
    this.ticket_id = payload.ticket_id;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }

  get dtsModeText() {
    return this.dts_mode === 'full' ? t('一次性全备迁移') : t('持续增量迁移');
  }

  get forcedTerminationDisableTips() {
    if (
      [
        STATUS.DISCONNECTED,
        STATUS.DISCONNECTING,
        STATUS.FULL_ONLINE,
        STATUS.FULL_SUCCESS,
        STATUS.INCR_SUCCESS,
        STATUS.TERMINATED,
        STATUS.TODO,
      ].includes(this.status)
    ) {
      return t('迁移任务：n，不支持该操作', { n: MigrateRecord.statusTextMap[this.status] });
    }
    return '';
  }

  get isFull() {
    return this.dts_mode === 'full';
  }

  get isRunning() {
    return [STATUS.DISCONNECTING, STATUS.FULL_ONLINE, STATUS.INCR_ONLINE, STATUS.TODO].includes(this.status);
  }

  get isSuccess() {
    return [STATUS.FULL_SUCCESS, STATUS.INCR_SUCCESS].includes(this.status);
  }

  get tagetDb() {
    return this.dts_config.map((item) => item.target_db_name);
  }

  get terminateSynceDisableTips() {
    if (
      [
        STATUS.DISCONNECTED,
        STATUS.DISCONNECTING,
        STATUS.FULL_FAILED,
        STATUS.FULL_ONLINE,
        STATUS.FULL_SUCCESS,
        STATUS.INCR_FAILED,
        STATUS.INCR_SUCCESS,
        STATUS.TERMINATED,
        STATUS.TODO,
      ].includes(this.status)
    ) {
      return t('迁移任务：n，不支持该操作', { n: MigrateRecord.statusTextMap[this.status] });
    }
    return '';
  }
}
