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

// binlog 断层信息
export interface BinlogGaps {
  missing: number[];
  missing_count: number;
}

// 批次内单个分片的备份明细（batch_details / precheck shards 返回）
export default class RollbackBatchShard {
  backup_begin_time: string;
  backup_end_time: string;
  binlog_gaps: BinlogGaps | null;
  current_master: string | null;
  files: {
    file_name: string;
    size: number;
    task_id: string;
  }[];
  in_current_topology: boolean;
  is_complete: boolean;
  shard_value: string;
  size: number;
  source_ip: string;
  source_is_current: boolean;
  source_port: number;

  constructor(payload = {} as RollbackBatchShard) {
    this.backup_begin_time = payload.backup_begin_time;
    this.backup_end_time = payload.backup_end_time;
    this.binlog_gaps = payload.binlog_gaps;
    this.current_master = payload.current_master;
    this.files = payload.files;
    this.in_current_topology = payload.in_current_topology;
    this.is_complete = payload.is_complete;
    this.size = payload.size;
    this.shard_value = payload.shard_value;
    this.source_ip = payload.source_ip;
    this.source_is_current = payload.source_is_current;
    this.source_port = payload.source_port;
  }
}
