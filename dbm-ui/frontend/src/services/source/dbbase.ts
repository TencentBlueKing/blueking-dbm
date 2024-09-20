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

import { ClusterTypes } from '@common/const';

import http from '../http';

const path = '/apis/dbbase';

/**
 * 查询集群名字是否重复
 */
export function verifyDuplicatedClusterName(params: { cluster_type: string; name: string; bk_biz_id: number }) {
  return http.get<boolean>(`${path}/verify_duplicated_cluster_name/`, params);
}

/**
 * 根据过滤条件查询集群详细信息
 */
export function filterClusters<
  T extends {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_cloud_name: string;
    cluster_name: string;
    cluster_type: string;
    master_domain: string;
    id: number;
  },
>(params: { bk_biz_id: number; exact_domain?: string; cluster_ids?: string }) {
  return http.get<T[]>(`${path}/filter_clusters/`, params);
}

/*
 * 查询业务下集群的属性字段
 * 集群通用接口，用于查询/操作集群公共的属性
 */
export function queryBizClusterAttrs(params: {
  bk_biz_id: number;
  cluster_type: ClusterTypes;
  cluster_attrs?: string;
  instances_attrs?: string;
  limit?: number;
  offset?: number;
}) {
  return http.get<
    Record<
      string,
      {
        value: string;
        text: string;
      }[]
    >
  >(`${path}/query_biz_cluster_attrs/`, params);
}

/**
 * 查询资源池,污点主机管理表头筛选数据
 */
export function queryResourceAdministrationAttrs(params: { resource_type: string; limit?: number; offset?: number }) {
  return http.get<
    Record<
      string,
      {
        value: string;
        text: string;
      }[]
    >
  >(`${path}/query_resource_administration_attrs/`, params);
}

/**
 * webconsole查询
 */
export function queryWebconsole(params: { cluster_id: number; cmd: string }) {
  return http.post<{
    query: string | Record<string, string>[];
    error_msg?: string;
  }>(`${path}/webconsole/`, params);
}

// 查询集群的库是否存在
export function checkClusterDatabase(params: { bk_biz_id: number; cluster_id: number; db_list: string[] }) {
  return http.post<Record<string, boolean>>(`${path}/check_cluster_databases/`, params);
}

// 根据用户手动输入的ip[:port]查询真实的实例
export function checkInstance<
  T extends {
    bk_host_id: number;
    ip: string;
    bk_cloud_id: number;
  },
>(params: { instance_addresses: string[]; bk_biz_id: number }) {
  return http.post<T[]>(`${path}/check_instances/`, params);
}

// 查询全集群信息
export function queryAllTypeCluster(params: {
  bk_biz_id: number;
  cluster_types?: string;
  immute_domain?: string;
  phase?: string;
  limit?: number;
  offset?: number;
}) {
  return http.get<
    {
      bk_cloud_id: number;
      cluster_type: string;
      id: number;
      immute_domain: string;
      major_version: string;
      name: string;
      region: string;
    }[]
  >(`${path}/simple_query_cluster/`, params);
}
