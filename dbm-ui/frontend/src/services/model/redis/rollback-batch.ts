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

// 备份方式：SCHEDULED 例行备份 / BILL 单据备份
export enum BackupType {
  BILL = 'BILL',
  SCHEDULED = 'SCHEDULED',
}

// 备份批次摘要（list_batches 返回，轻量级，不含分片明细）
export default class RollbackBatch {
  backup_identify: string;
  backup_type: BackupType;
  end_time: string;
  is_all_shards_covered: boolean;
  is_complete: boolean;
  shard_count: number;
  source_is_all_current: boolean;
  start_time: string;
  total_size: number;

  constructor(payload = {} as Omit<RollbackBatch, 'backupTypeText'>) {
    this.backup_identify = payload.backup_identify;
    this.backup_type = payload.backup_type;
    this.end_time = payload.end_time;
    this.is_all_shards_covered = payload.is_all_shards_covered;
    this.is_complete = payload.is_complete;
    this.shard_count = payload.shard_count;
    this.source_is_all_current = payload.source_is_all_current;
    this.start_time = payload.start_time;
    this.total_size = payload.total_size;
  }

  // 备份方式文案：例行备份 / 单据备份
  get backupTypeText() {
    return this.backup_type === BackupType.BILL ? '单据备份' : '例行备份';
  }
}
