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

import http from '../http';
import type { HostSpec } from '../types/ticket';

const path = '/apis/infras';

/**
 * 查询服务器资源的城市信息
 */
export function getInfrasCities() {
  return http.get<{
    city_code: string,
    city_name: string,
    inventory: number,
    inventory_tag: string
  }[]>(`${path}/cities/`);
}

/**
 * 主机提交格式
 */
interface HostSubmitParams {
  ip: string,
  bk_cloud_id: number,
  bk_host_id: number,
  bk_cpu?: number,
  bk_mem?: number,
  bk_disk?: number,
  bk_biz_id: number
}

/**
 * redis 容量列表
 */
export function getCapSpecs(params: {
  nodes: {
    master: Array<HostSubmitParams>,
    slave: Array<HostSubmitParams>
  },
  ip_source: string
  cluster_type: string
  cityCode: string
}) {
  return http.post<{
    group_num: number,
    maxmemory: number,
    shard_num: number,
    spec: string,
    total_memory: number
    cap_key: string,
    selected: boolean
    max_disk: number,
    total_disk: string,
  }[]>(`${path}/cities/cap_specs/`, params);
}

/**
 * 查询集群类型
 */
export function fetchDbTypeList() {
  return http.get<Array<{
    id: string,
    name: string
  }>>(`${path}/dbtype/list_db_types/`);
}

/**
 * 服务器规格列表
 */
export function getInfrasHostSpecs() {
  return http.get<HostSpec[]>(`${path}/cities/host_specs/`);
}
