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
import RedisRollbackModel from '@services/model/redis/redis-rollback';
import RollbackBatch from '@services/model/redis/rollback-batch';
import RollbackBatchShard from '@services/model/redis/rollback-batch-shard';
import type { ListBase } from '@services/types';

import http from '../http';

const getRootPath = () => `/apis/redis/bizs/${window.PROJECT_CONFIG.BIZ_ID}/rollback`;

// 备份批次相关接口
const getBatchesRootPath = () => `${getRootPath()}/batches`;

export function getRollbackList(
  params?: {
    bk_biz_id: number;
    limit?: number;
    offset?: number;
    temp_cluster_proxy?: string; // ip:port
  } & Record<string, any>,
) {
  return http.get<ListBase<RedisRollbackModel[]>>(`${getRootPath()}/`, params).then((res) => ({
    ...res,
    results: res.results.map((item) => new RedisRollbackModel(item)),
  }));
}

// 查询集群在指定时间窗口内的备份批次摘要列表（end_time - start_time 跨度不得超过 30 天）
export function getRollbackBatches(params: {
  cluster_id: number;
  end_time?: string;
  shard_values?: string[];
  start_time?: string;
}) {
  return http
    .post<{
      batches: RollbackBatch[];
      cluster_shards: {
        current_master: string;
        current_slave: string;
        resolvable: boolean;
        shard_value: string;
        warning: string;
      }[];
      locator_source: string;
    }>(`${getBatchesRootPath()}/list_batches/`, params)
    .then((res) => ({
      ...res,
      batches: res.batches.map((item) => new RollbackBatch(item)),
    }));
}

// 展开指定批次各分片的全备明细（仅指定分片时调用，整集群回档无需调用）
export function getRollbackBatchDetails(params: {
  backup_identify: string;
  cluster_id: number;
  shard_values?: string[];
}) {
  return http
    .post<{
      backup_identify: string;
      cluster_shards: Record<string, unknown>[];
      locator_source: string;
      shards: RollbackBatchShard[];
      warnings: string[];
    }>(`${getBatchesRootPath()}/batch_details/`, params)
    .then((res) => ({
      ...res,
      shards: res.shards.map((item) => new RollbackBatchShard(item)),
    }));
}

// 提单前预检：校验分片解析、选备完整性、分片覆盖、binlog 连续性与备份文件有效性
export function getRollbackPrecheck(params: {
  allow_binlog_nonconsecutive?: boolean;
  backup_identify: string;
  cluster_id: number;
  recovery_time_point?: string;
  resource_spec?: {
    redis: {
      count: number;
    };
  };
  shard_values?: string[];
}) {
  return http.post<{
    binlog_nonconsecutive: boolean;
    errors: string[];
    exist: boolean;
    shards: {
      binlog_gaps: { missing: number[]; missing_count: number } | null;
      errors: string[];
      file_names: string[];
      ok: boolean;
      shard_value: string;
    }[];
    warnings: string[];
  }>(`${getBatchesRootPath()}/precheck/`, params);
}

// 按 Key 反查所在分片（经接入层在线命令计算落点，传入 backup_identify 时求批次分片集合并集）
export function getShardRoute(params: { backup_identify?: string; cluster_id: number; keys: string[] }) {
  return http.post<{
    batch_shard_values: string[];
    results: {
      backend: string;
      batch_shard_values: string[];
      error: string;
      is_covered: boolean;
      key: string;
      range: string;
      uncovered_ranges: string[];
    }[];
    warnings: string[];
  }>(`${getBatchesRootPath()}/shard_route/`, params);
}
