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

import DbhaServiceStatusModel from '@services/model/db-extension/dbha-service-status';
import DnsServiceStatusModel from '@services/model/db-extension/dns-service-status';
import DrsServiceStatusModel from '@services/model/db-extension/drs-service-status';
import NgnixServiceStatusModel from '@services/model/db-extension/nginx-service-status';
import RedisDtsServiceStatusModel from '@services/model/db-extension/redis-dts-service-status';

import http from '../http';

const path = '/apis/dbextension';

/**
 * 获取可用云区域
 */
export function fetchAvailableClouds() {
  return http.get<
    {
      bk_cloud_id: number;
      bk_cloud_name: string;
    }[]
  >(`${path}/fetch_available_clouds/`);
}

/**
 * 云区域组件信息
 */
export function fetchExtensions(params: { bk_cloud_id: number }) {
  return http
    .get<{
      DBHA: DbhaServiceStatusModel[];
      DNS: DnsServiceStatusModel[];
      DRS: DrsServiceStatusModel[];
      NGINX: NgnixServiceStatusModel[];
      REDIS_DTS: RedisDtsServiceStatusModel[];
    }>(`${path}/fetch_extensions/`, params)
    .then((res) => ({
      DBHA: res.DBHA.map((item) => new DbhaServiceStatusModel(item)),
      DNS: res.DNS.map((item) => new DnsServiceStatusModel(item)),
      DRS: res.DRS.map((item) => new DrsServiceStatusModel(item)),
      NGINX: res.NGINX.map((item) => new NgnixServiceStatusModel(item)),
      REDIS_DTS: res.REDIS_DTS.map((item) => new RedisDtsServiceStatusModel(item)),
    }));
}
