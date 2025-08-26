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

import type { InstanceInfos, ListBase, MachineInfos } from '@services/types';

import { ClusterTypes, DBTypes } from '@common/const';

import http, { type IRequestPayload } from '../http';

const path = '/apis/dbbase';

/**
 * 查询集群名字是否重复
 */
export function verifyDuplicatedClusterName(params: { bk_biz_id: number; cluster_type: string; name: string }) {
  return http.get<boolean>(`${path}/verify_duplicated_cluster_name/`, params);
}

/**
 * 根据过滤条件查询集群详细信息，返回的字段和集群列表接口相同
 */
export function filterClusters<
  T extends {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_cloud_name: string;
    cluster_name: string;
    cluster_type: string;
    db_module_id: number;
    db_module_name: string;
    db_type: string;
    id: number;
    major_version: string;
    master_domain: string;
  },
>(params: {
  bk_biz_id: number;
  cluster_ids?: string;
  cluster_type?: string;
  db_type?: DBTypes;
  domain?: string;
  exact_domain?: string;
}) {
  return http.get<T[]>(`${path}/filter_clusters/`, params);
}

/*
 * 查询业务下集群的属性字段
 * 集群通用接口，用于查询/操作集群公共的属性
 */
export function queryBizClusterAttrs(params: {
  bk_biz_id: number;
  cluster_attrs?: string;
  cluster_type: ClusterTypes;
  instances_attrs?: string;
  limit?: number;
  offset?: number;
}) {
  return http.get<
    Record<
      string,
      {
        text: string;
        value: string;
      }[]
    >
  >(`${path}/query_biz_cluster_attrs/`, params, {
    cache: 1000,
  });
}

/**
 * 查询资源池,污点主机管理表头筛选数据
 */
export function queryResourceAdministrationAttrs(params: { limit?: number; offset?: number; resource_type: string }) {
  return http.get<
    Record<
      string,
      {
        text: string;
        value: string;
      }[]
    >
  >(`${path}/query_resource_administration_attrs/`, params, {
    cache: 1000,
  });
}

/**
 * webconsole查询
 */
export function queryWebconsole(params: { cluster_id: number; cmd: string; options?: Record<string, unknown> }) {
  return http.post<{
    error_msg?: string;
    query: string | Record<string, string>[];
  }>(`${path}/webconsole/`, params);
}

// 查询集群的库是否存在
export function checkClusterDatabase(params: { bk_biz_id: number; cluster_id: number; db_list: string[] }) {
  return http.post<Record<string, boolean>>(`${path}/check_cluster_databases/`, params);
}

// 批量查询集群的库是否存在
export function batchCheckClusterDatabase(params: { bk_biz_id: number; cluster_ids: number[]; db_list: string[] }) {
  return http.post<{
    [clusterId: string]: {
      [dbName: string]: boolean;
    };
  }>(`${path}/batch_check_cluster_databases/`, params);
}

// 根据用户手动输入的ip[:port]查询真实的实例
export function checkInstance<T extends InstanceInfos>(params: {
  bk_biz_id?: number;
  cluster_ids?: number[];
  cluster_type?: ClusterTypes[];
  db_type?: DBTypes;
  instance_addresses: string[];
  instance_role?: string[];
}) {
  return http.post<T[]>(`${path}/check_instances/`, params);
}

// 查询全集群信息
export function queryAllTypeCluster(params: {
  bk_biz_id: number;
  cluster_types?: string;
  immute_domain?: string;
  limit?: number;
  offset?: number;
  phase?: string;
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

// 查询集群实例数量
export function queryClusterInstanceCount(params: { bk_biz_id: number }) {
  return http.get<
    Record<
      ClusterTypes,
      {
        cluster_count: number;
        instance_count: number;
      }
    >
  >(`${path}/query_cluster_instance_count/`, params, {
    cache: 1000,
  });
}

export function updateClusterAlias(params: { cluster_id: number; new_alias: string }) {
  return http.post(`${path}/update_cluster_alias/`, {
    ...params,
    bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
  });
}

export function queryClusterStat(params: { bk_biz_id: number; cluster_type: string }, payload = {} as IRequestPayload) {
  return http.get<
    Record<
      number,
      {
        in_use: number;
        total: number;
        used: number;
      }
    >
  >(
    `${path}/query_cluster_stat/`,
    {
      ...params,
    },
    payload,
  );
}

// dbconsole查询
export function dbConsole(params: {
  cmd: string;
  db_type: string;
  instances: {
    bk_cloud_id: number;
    instance: string;
  }[];
  is_proxy?: boolean;
}) {
  return http.post<
    {
      error_msg: string;
      instance: string;
      table_data: Record<string, string>[];
    }[]
  >(`${path}/dbconsole/`, params);
}

// 批量增加集群标签键
export function addClusterTagKeys(params: { bk_biz_id: number; cluster_ids: number[]; tags: number[] }) {
  return http.post(`${path}/add_cluster_tag_keys/`, params);
}

// 批量移除集群标签键
export function removeClusterTagKeys(params: { bk_biz_id: number; cluster_ids: number[]; keys: string[] }) {
  return http.post(`${path}/remove_cluster_tag_keys/`, params);
}

// 更新集群标签
export function updateClusterTag(params: { bk_biz_id: number; cluster_id: number; tags: number[] }) {
  return http.post(`${path}/update_cluster_tag/`, params);
}

// 查询全局实例
export function getGlobalInstance(params: {
  bk_biz_id?: number; // 业务ID
  cluster_id?: number; // 集群ID
  cluster_type?: string; // 集群类型
  db_module_id?: number; // 模块ID
  db_type: DBTypes; // 数据库类型
  domain?: string; // 域名查询
  exact_ip?: string; // 精确IP查询
  group_id?: string; // 分组ID
  instance_address?: string; // 实例地址查询
  ip?: string; // 主机IP查询
  limit?: number;
  offset?: number;
  port?: string; // 端口查询
  role?: string; // 过滤的实例角色
  status?: string; // 实例状态
}) {
  return http.get<ListBase<({ bk_biz_id: number } & InstanceInfos)[]>>(`${path}/filter_instances/`, params);
}

// 查询全局主机
export function getGlobalMachine(params: {
  add_role_count?: boolean; // 是否增加角色数量
  bk_agent_id?: string; // agent ID
  bk_biz_id?: number; // 业务ID
  bk_city_name?: string; // 城市名称
  bk_cloud_id?: number; // 云区域ID
  bk_host_id?: number; // 主机ID
  bk_os_name?: string; // 操作系统
  cluster_ids?: string; // 集群ID列表
  cluster_status?: string;
  cluster_type?: string;
  creator?: string; // 创建人
  db_module_id?: number; // 模块ID
  db_type: DBTypes; // 数据库类型
  instance_address?: string;
  instance_role?: string; // 实例角色
  instance_status?: string; // 实例状态
  ip?: string; // 主机IP
  limit?: number; // 分页限制
  machine_type?: string; // 机器类型
  offset?: number;
  spider_role?: string; // spider角色
}) {
  return http.get<ListBase<MachineInfos[]>>(`${path}/filter_machines/`, params);
}

// 查询全局集群
export function getGlobalCluster<
  T extends {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_cloud_name: string;
    cluster_name: string;
    cluster_type: string;
    db_module_id: number;
    db_module_name: string;
    db_type: string;
    id: number;
    major_version: string;
    master_domain: string;
  },
>(params: {
  bk_biz_id?: number;
  cluster_ids?: string;
  cluster_type?: string;
  db_type: DBTypes;
  domain?: string;
  exact_domain?: string;
  limit?: number;
  offset?: number;
}) {
  return http.get<T[]>(`${path}/filter_clusters_by_type/`, params);
}

/**
 * 查询集群负载
 */
export function queryClusterLoad(params: { bk_biz_id: number; cluster_type: string }, payload = {} as IRequestPayload) {
  return http.get<{
    cluster_load_data_map: {
      [domain: string]: {
        [cluster_type: string]: {
          cpu: {
            [ip: string]: number;
          } & {
            high_load: boolean;
            low_load: boolean;
          };
          mem: {
            [ip: string]: number;
          } & {
            high_load: boolean;
            low_load: boolean;
          };
          // connections: {};
        };
      };
    };
    cluster_load_status_map: {
      [domain: string]: {
        [cluster_type: string]: {
          high_load: boolean;
          low_load: boolean;
        };
      } & {
        high_load: boolean;
        low_load: boolean;
      };
    };
  }>(`${path}/query_cluster_load/`, params, payload);
}
