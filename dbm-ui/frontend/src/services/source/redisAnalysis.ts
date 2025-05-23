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
import RedisHotKeyModel from '@services/model/redis/redis-hot-key';
import type { ListBase } from '@services/types';

const getRootPath = () => `/apis/redis/bizs/${window.PROJECT_CONFIG.BIZ_ID}/analysis`;
const getDetailRootPath = () => `/apis/redis/bizs/${window.PROJECT_CONFIG.BIZ_ID}/analysis_details`;

/**
 * 获取热key分析记录
 */
export function queryAnalysisRecords(params: {
  cluster_ids?: string;
  create_at__gte?: string;
  create_at__lte?: string;
  immute_domain?: string;
  instance_addresses?: string;
  limit?: number;
  offset?: number;
  operator?: string;
}) {
  return http.get<ListBase<RedisHotKeyModel[]>>(`${getRootPath()}/query_analysis_records/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new RedisHotKeyModel(item)),
  }));
}

/**
 * 获取热key分析记录详情
 */
export function getAnalysisDetails(params: {
  instance_addresses?: string;
  key?: string;
  limit?: number;
  offset?: number;
  record_id: number;
}) {
  return http.get<
    Record<
      string,
      Array<{
        cmd_info: string;
        exec_count: number;
        id: number;
        key: string;
        ratio: string;
      }>
    >
  >(`${getDetailRootPath()}/get_analysis_details/`, params);
}

/**
 * 导出热key分析记录为 excel 文件
 */
export function exportHotKeyAnalysis(params: {
  instance_addresses?: string;
  key?: string;
  limit?: number;
  offset?: number;
  record_ids: string;
}) {
  return http.get<string>(`${getDetailRootPath()}/export_hot_key_analysis/`, params, { responseType: 'blob' });
}
