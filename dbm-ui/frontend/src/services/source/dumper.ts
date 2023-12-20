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

import DumperModel from '@services/model/dumper/dumper';

import { useGlobalBizs } from '@stores';

import http from '../http';
import type { ListBase } from '../types/common';

const { currentBizId } = useGlobalBizs();

interface DumperConfig {
  add_type: string;
  bk_biz_id: number;
  create_at: string;
  creator: string;
  dumper_instances: Array<{
    dumper_id: number;
    protocol_type: string;
    source_cluster_domain: string;
    target_address: string;
  }>;
  dumper_process_ids: number[];
  id: number;
  instance_count: number;
  name: string;
  repl_tables: Array<{
    db_name: string;
    table_names: string[];
  }>;
  running_tickets: number[];
  update_at: string;
  updater: string;
}

/**
 * 查询数据订阅配置列表
 */
export function listDumperConfig(params: {
  db_name?: string,
  table_name?: string,
  limit?: number
  offset?: number,
}) {
  return http.get<ListBase<DumperConfig[]>>(`/apis/mysql/bizs/${currentBizId}/dumper_config/`, params);
}

/**
 * 新建数据订阅配置
 */
export const createDumperConfig = function (params: Omit<DumperConfig, 'id'>) {
  return http.post<any>(`/apis/mysql/bizs/${currentBizId}/dumper_config/`, params);
};

/**
 * 校验订阅配置是否重名
 */
export function verifyDuplicateName(params: {
  name: string,
}) {
  return http.get<any>(`/apis/mysql/bizs/${currentBizId}/dumper_config/verify_duplicate_name/`, params);
}

/**
 * 数据订阅配置详情
 */
export function getDumperConfigDetail(params: {
  id: number,
}) {
  return http.get<DumperConfig>(`/apis/mysql/bizs/${currentBizId}/dumper_config/${params.id}/`, params);
}

/**
 * 更新数据订阅配置
 */
export function updateDumperConfig(params: DumperConfig) {
  return http.put<DumperConfig>(`/apis/mysql/bizs/${currentBizId}/dumper_config/${params.id}/`, params);
}

/**
 * 更新部分数据订阅配置
 */
export function updateDumperConfigPartial(params: Partial<DumperConfig>) {
  return http.patch<DumperConfig>(`/apis/mysql/bizs/${currentBizId}/dumper_config/${params.id}/`, params);
}

/**
 * 删除数据订阅配置
 */
export function deleteDumperConfig(params: {
  id: number,
}) {
  return http.delete<null>(`/apis/mysql/bizs/${currentBizId}/dumper_config/${params.id}/`, params);
}

/**
 * 查询数据订阅实例列表
 */
export function listDumperInstance(params: {
  ip?: string,
  dumper_id?: string,
  source_cluster?: string,
  receiver_type?: string,
  start_time?: string,
  end_time?: string,
}) {
  return http.get<ListBase<DumperModel[]>>(`/apis/mysql/bizs/${currentBizId}/dumper_instance/`, params).then(data => ({
    ...data,
    results: data.results.map(item => new DumperModel(item)),
  }));
}
