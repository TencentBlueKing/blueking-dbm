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

import InfluxdbInstanceModel from '@services/model/influxdb/influxdbInstance';

import { useGlobalBizs } from '@stores';

import http from '../http';
import type { ListBase } from '../types';

const { currentBizId } = useGlobalBizs();

const path = `/apis/bigdata/bizs/${currentBizId}/influxdb/influxdb_resources`;

/**
 * 获取实例列表
 */
export function getInfluxdbInstanceList(params: Record<string, any> & { bk_biz_id: number }) {
  return http.get<ListBase<InfluxdbInstanceModel[]>>(`${path}/list_instances/`, params)
    .then(res => ({
      ...res,
      results: res.results.map((item: InfluxdbInstanceModel) => new InfluxdbInstanceModel(item)),
    }));
}

/**
 * 获取实例详情
 */
export function retrieveInfluxdbInstance(params: {
  bk_biz_id: number,
  instance_address: string
}) {
  return http.get<InfluxdbInstanceModel>(`${path}/retrieve_instance/`, params)
    .then(data => new InfluxdbInstanceModel(data));
}

/**
 * 导出集群数据为 excel 文件
 */
export function exportInfluxdbClusterToExcel(params: { cluster_ids?: number[] }) {
  return http.post<string>(`${path}/export_cluster/`, params);
}

/**
 * 导出实例数据为 excel 文件
 */
export function exportInfluxdbInstanceToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${path}/export_instance/`, params);
}

