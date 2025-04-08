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

const path = '/apis/infras';

/**
 * 查询服务器资源的城市信息
 */
export function getInfrasCities() {
  return http.get<
    {
      city_code: string;
      city_name: string;
      inventory: number;
      inventory_tag: string;
    }[]
  >(`${path}/cities/`);
}

/**
 * 查询服务器资源的城市信息
 */
export function listLogicCities() {
  return http.get<
    {
      bk_idc_city_id: number;
      bk_idc_city_name: string;
      logical_city: number;
      logical_city_name: string;
    }[]
  >(`${path}/cities/list_logic_cities/`);
}

/**
 * 查询城市园区信息
 */
export function getInfrasSubzonesByCity(params: { city_code: string }) {
  return http.get<
    {
      bk_city: number;
      bk_city_code: string;
      bk_sub_zone: string;
      bk_sub_zone_id: number;
    }[]
  >(`${path}/cities/list_subzones/`, params);
}

/**
 * redis 容量列表
 */
export function getCapSpecs(params: {
  cityCode: string;
  cluster_type: string;
  ip_source: string;
  nodes: {
    master: Array<{
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_cpu?: number;
      bk_disk?: number;
      bk_host_id: number;
      bk_mem?: number;
      ip: string;
    }>;
    slave: Array<{
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_cpu?: number;
      bk_disk?: number;
      bk_host_id: number;
      bk_mem?: number;
      ip: string;
    }>;
  };
}) {
  return http.post<
    {
      cap_key: string;
      group_num: number;
      max_disk: number;
      maxmemory: number;
      selected: boolean;
      shard_num: number;
      spec: string;
      total_disk: string;
      total_memory: number;
    }[]
  >(`${path}/cities/cap_specs/`, params);
}

/**
 * 查询集群类型
 */
export function fetchDbTypeList() {
  return http.get<
    Array<{
      id: string;
      name: string;
    }>
  >(`${path}/dbtype/list_db_types/`);
}

/**
 * 服务器规格列表
 */
export function getInfrasHostSpecs() {
  return http.get<
    {
      cpu: string;
      mem: string;
      spec: string;
      type: string;
    }[]
  >(`${path}/cities/host_specs/`);
}
