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

import http from './http';
import type { ListBase } from './types';

// 获取实例列表
export const getListInstance = function (params: Record<string, any> & { bk_biz_id: number }) {
  return http
    .get<
      ListBase<InfluxdbInstanceModel[]>
    >(`/apis/bigdata/bizs/${params.bk_biz_id}/influxdb/influxdb_resources/list_instances/`, params)
    .then((res) => ({
      ...res,
      results: res.results.map((item: InfluxdbInstanceModel) => new InfluxdbInstanceModel(item)),
    }));
};

// 获取实例详情
export const getInstanceDetails = function (params: { bk_biz_id: number; instance_address: string }) {
  return http
    .get<InfluxdbInstanceModel>(
      `/apis/bigdata/bizs/${params.bk_biz_id}/influxdb/influxdb_resources/retrieve_instance/`,
      params,
    )
    .then((data) => new InfluxdbInstanceModel(data));
};
