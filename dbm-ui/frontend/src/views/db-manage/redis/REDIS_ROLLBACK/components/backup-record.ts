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
import dayjs from 'dayjs';

import { BackupType } from '@services/model/redis/rollback-batch';

import { useTimeZoneFormat } from '@hooks';

import { t } from '@locales/index';

// 行内已选的备份记录快照（选择器确认后写入行数据）
export interface IBackupRecord {
  allow_binlog_nonconsecutive: boolean;
  // 备份批次标识
  backup_identify: string;
  backup_type: BackupType;
  // 当前拓扑分片数（用于拓扑不一致提示）
  current_shard_count: number;
  // 批次最晚一个分片全备完成时间（UTC），作为「构造到」的下限
  end_time: string;
  // 构造到的时间点（本地时区显示格式），空串表示仅用全备
  recovery_time_point: string;
  scope: 'all' | 'pick';
  // 备份时分片数
  shard_count: number;
  // 参与构造分片中最晚的全备结束时间（UTC），指定分片时重算
  shard_max_backup_end_time: string;
  // 指定分片时勾选的分片值，全部时为 []
  shard_values: string[];
  start_time: string;
}

export type PrecheckState = 'unset' | 'pass' | 'warning' | 'fail';

export interface IPrecheckResult {
  message: string;
  state: PrecheckState;
}

export const createBackupRecord = (values = {} as Partial<IBackupRecord>): IBackupRecord => ({
  allow_binlog_nonconsecutive: false,
  backup_identify: '',
  backup_type: BackupType.SCHEDULED,
  current_shard_count: 0,
  end_time: '',
  recovery_time_point: '',
  scope: 'all',
  shard_count: 0,
  shard_max_backup_end_time: '',
  shard_values: [],
  start_time: '',
  ...values,
});

// 备份方式文案：标识前缀 BILL 为单据备份，其余为例行备份
export const getBackupTypeText = (identify: string) => (identify.startsWith('BILL') ? t('单据备份') : t('例行备份'));

// TendisSSD / TendisPlus 有 binlog，可填写构造到
export const hasBinlog = (clusterType: string) => /tendisssd|tendisplus/i.test(clusterType);

export const getScopeText = (record: IBackupRecord) =>
  record.scope === 'all'
    ? t('全部（n 个分片）', { n: record.shard_count })
    : t('指定分片（n 个）', { n: record.shard_values.length });

// 页面所选时区的偏移（如 +08:00），未选择时回退浏览器时区
export const getTimeZoneOffset = () => {
  const { timeZone } = useTimeZoneFormat();
  return timeZone.value.utc || dayjs().format('Z');
};

// UTC 时间转页面所选时区的展示格式（回填时间选择器、时间展示用）
export const utcToLocal = (utcTime: string) => {
  if (!utcTime) {
    return '';
  }
  return dayjs.utc(utcTime).utcOffset(getTimeZoneOffset()).format('YYYY-MM-DD HH:mm:ss');
};
