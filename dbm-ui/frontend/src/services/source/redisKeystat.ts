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

import http from '@services/http';
import RedisKeystatAnalysisModel from '@services/model/redis/redis-keystat-analysis';
import type { ListBase } from '@services/types';

const getRootPath = () => `/apis/redis/bizs/${window.PROJECT_CONFIG.BIZ_ID}/keystat`;
const getDetailRootPath = () => `/apis/redis/bizs/${window.PROJECT_CONFIG.BIZ_ID}/keystat_details`;

/**
 * 获取redis实例分析相关信息
 */
export function getKeystatInfoByInstance(params: { instances: string }) {
  return http.get<
    Record<
      string,
      {
        cluster_domain: string;
        instance: string;
        key_num: number;
        memory_total: number;
        value: number;
      }
    >
  >(`${getRootPath()}/keystat_info_by_instance/`, params);
}

/**
 * 获取redis内存分析记录
 */
export function queryKeystatRecords(params: {
  cluster_ids?: string;
  create_at__gte?: string;
  create_at__lte?: string;
  immute_domain?: string;
  instance_addresses?: string;
  limit?: number;
  offset?: number;
  operator?: string;
  record_id?: number;
  status?: string;
  ticket_id: number;
}) {
  return http
    .get<ListBase<RedisKeystatAnalysisModel[]>>(`${getRootPath()}/query_keystat_records/`, params)
    .then((data) => ({
      ...data,
      results: data.results.map((item) => new RedisKeystatAnalysisModel(item)),
    }));
}

/**
 * 获取redis内存分析记录详情
 */
export function getKeyStatDetails(params: {
  key_class?: string;
  key_type?: string;
  limit?: number;
  offset?: number;
  record_id: number;
}) {
  return http.get<
    ListBase<
      {
        avg_key_length: number;
        avg_key_used_bytes: number;
        avg_ttl: string;
        avg_ttl_human: string;
        count: number;
        count_with_ttl: number;
        key_class: string;
        key_name: string;
        key_type: string;
        mem_used_bytes: number;
        mem_used_pct: number;
        min_idletime: string;
        min_idletime_show: number;
      }[]
    >
  >(`${getDetailRootPath()}/get_keystat_details/`, params);
}

/**
 * 获取redis内存分析大Key排行榜
 */
export function getKeystatRank(params: { key_class?: string; key_name?: string; record_id: number }) {
  return http.get<
    Array<{
      key_length: number;
      key_name: string;
      key_type: string;
      member: number;
      member_len: number;
      memory_size: number;
      ttl: number;
      ttl_human: number;
      value_size: number;
    }>
  >(`${getDetailRootPath()}/get_keystat_rank/`, params);
}

/**
 * 导出内存分析记录
 */
export function exportKeystatAnalysis(params: { record_ids: string }) {
  return http.get<string>(`${getDetailRootPath()}/export_keystat_analysis/`, params, { responseType: 'blob' });
}
