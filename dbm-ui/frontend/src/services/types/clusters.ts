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

import type {
  HostDetails,
  ResourceItem,
} from '../types';

/**
 * 用来获取集群节点的 keys
 */
export enum ClusterNodeKeys {
  PROXY = 'proxy',
  REDIS_MASTER = 'redis_master',
  REDIS_SLAVE = 'redis_slave'
}
export type ClusterNodeKeyValues = `${ClusterNodeKeys}`;

/**
 * 查询资源列表参数
 */
export interface GetResourcesParams {
  bk_biz_id: number,
  limit: number,
  offset: number,
  type: string,
  cluster_ids?: number[] | number,
}

/**
 * 查询资源列表返回结果
 */
export interface ResourcesResult<T> {
  count: number,
  next: string,
  previous: string,
  results: T[]
}

/**
 * redis 资源信息
 */
export interface ResourceRedisItem {
  bk_biz_id: number,
  bk_biz_name: string,
  bk_cloud_id: number,
  bk_cloud_name: string,
  cluster_alias: string,
  cluster_name: string,
  cluster_type: string,
  create_at: string,
  creator: string,
  dns_to_clb: boolean,
  update_at: string,
  updater: string,
  db_module_name: string
  id: number
  master_domain: string
  slave_domain: string[]
  phase: 'online' | 'offline',
  status: string,
  cluster_entry: {
    entry: string,
    cluster_entry_type: string,
    role: string,
  }[],
  cluster_entry_details: {
    cluster_entry_type: string,
    entry: string,
    role: string,
    target_details: {
      app: string,
      bk_cloud_iduid: number,
      dns_str: string,
      domain_name: string,
      domain_typeuid: number,
      ip: string,
      last_change_time: string,
      manager: string,
      port: number,
      remark: string,
      start_time: string,
      status: string,
      uid: number,
    }[]
  }[];
  operations: Array<{
    cluster_id: number,
    flow_id: number,
    status: string,
    ticket_id: number,
    ticket_type: string,
    title: string,
  }>
  [ClusterNodeKeys.REDIS_MASTER]: ResourceItem['masters']
  [ClusterNodeKeys.PROXY]: ResourceItem['masters']
  [ClusterNodeKeys.REDIS_SLAVE]: ResourceItem['masters']
}

/**
 * 查询资源表格列返回结果
 */
export interface TableFieldsItem {
  key: string,
  name: string,
}

/**
 * 查询资源表格参数
 */
export interface TableFieldsParams {
  bk_biz_id: number,
  type: string
}

/**
 * 获取资源详情参数
 */
export interface ResourceParams {
  bk_biz_id: number,
  id: number,
  type: string
}

/**
 * 获取资源实例列表参数
 */
export interface ResourceInstancesParams {
  bk_biz_id: number,
  type: string,
  db_type: string,
  limit?: number,
  offset?: number,
  instance_address?: string,
  domain?: string,
  status?: string,
  ip?: string,
  port?: string,
  cluster_id?: number
  role?: string
}

/**
 * 资源实例信息
 */
// export interface ResourceInstance {
//   bk_cloud_id: number,
//   bk_cloud_name: string,
//   bk_host_id: number,
//   cluster_id: number,
//   cluster_name: string,
//   cluster_type: string,
//   create_at: string,
//   db_module_id: number,
//   host_info: HostDetails,
//   id: number,
//   instance_address: string,
//   ip: string,
//   master_domain: string,
//   port: number,
//   related_clusters?: {
//     alias: string,
//     bk_biz_id: number,
//     bk_cloud_id: number,
//     cluster_name: string,
//     cluster_type: string,
//     creator: string,
//     db_module_id: number,
//     id: number,
//     major_version: string,
//     master_domain: string,
//     phase: string,
//     region: string,
//     status: string,
//     time_zone: string
//     updater: string,
//   }[],
//   role: string,
//   slave_domain: string,
//   spec_config: {
//     id: number
//   }
//   status: string,
//   version: string,
// }

/**
 * 获取集群拓扑参数
 */
export interface ResourceTopoParams {
  type: string,
  bk_biz_id: number,
  resource_id: number
}

export interface GetClusterHostNodesRequestParam {
  db_type: string;
  bk_biz_id: string;
  cluster_id: string;
}

/**
 * 集群详情拓扑图 node
 */
export interface ResourceTopoNode {
  node_id: string,
  node_type: string
  url: string
}

/**
 * 集群详情拓扑图 group
 */
export interface ResourceTopoGroup {
  node_id: string,
  group_name: string,
  children_id: string[],
}

/**
 * 集群详情拓扑图 line
 */
export interface ResourceTopoLine {
  source: string,
  source_type: string,
  target: string,
  target_type: string,
  label: string,
  label_name: string
}

/**
 * 获取集群实例详情参数
 */
export interface InstanceDetailsParams {
  bk_biz_id: number,
  type: string,
  instance_address: string,
  cluster_id?: number
}

/**
 * 集群实例详情
 */
export interface InstanceDetails {
  bk_cloud_id: number,
  bk_cpu: number,
  bk_disk: number,
  bk_host_id: number,
  bk_host_innerip: string,
  bk_mem: number,
  bk_os_name: string,
  cluster_id: number,
  cluster_type: string,
  create_at: string,
  idc_city_id: string,
  idc_city_name: string,
  idc_id: number,
  instance_address: string,
  master_domain: string,
  net_device_id: string,
  rack: string,
  rack_id: number,
  role: string,
  slave_domain: string,
  status: string,
  sub_zone: string,
  db_module_id: number,
  cluster_type_display: string,
  bk_idc_name: string,
  bk_cloud_name: string,
  db_version: string,
  version?: string
}

/**
 * 查询主机节点列表参数
 */
export interface ClusterNodesParams {
  bk_biz_id: number,
  cluster_id: number,
  db_type: string,
  type: string,
  role: string,
  keyword?: string
}

/**
 * 获取集群密码参数
 */
export interface ClusterPasswordParams {
  bk_biz_id: number,
  cluster_id: number,
  db_type: string,
  type: string,
}
/**
 * 集群密码
 */
export interface ClusterPassword {
  cluster_name: string,
  domain: string,
  password: string
}

/**
 * 实例详细信息（包含主机、集群）
 */
export interface InstanceInfos {
  bk_cloud_id: number,
  bk_cloud_name: string,
  bk_host_id: number,
  cluster_id: number,
  cluster_name: string,
  cluster_type: string,
  cluster_domain: string;
  create_at: string,
  host_info: HostDetails,
  instance_address: string,
  ip: string,
  master_domain: string,
  port: number,
  related_clusters: {
    alias: string,
    bk_biz_id: number,
    bk_cloud_id: number,
    cluster_name: string,
    cluster_type: string,
    creator: string,
    db_module_id: number,
    id: number,
    major_version: string,
    master_domain: string,
    phase: string,
    region: string,
    status: string,
    time_zone: string
    updater: string,
  }[],
  role: string,
  spec_config: {
    cpu: number;
    id: number;
    mem: number;
    name: string;
    storage_spec: {
      mount_point: string;
      size: number;
      type: string;
    }
  },
  status: 'running' | 'unavailable',
}

/**
 * mysql 工具箱集群信息
 */
export interface MySQLClusterInfos {
  alias: string,
  bk_biz_id: number,
  bk_cloud_id: number,
  cluster_name: string,
  cluster_type: string,
  creator: string,
  db_module_id: number,
  db_module_name: string,
  id: number,
  instance_count: number,
  major_version: string,
  master_domain: string,
  masters: {
    bk_biz_id: number,
    bk_cloud_id: number,
    bk_host_id: number,
    bk_instance_id: number,
    instance: string,
    ip: string,
    name: string,
    phase: string,
    port: number,
    spec_config: {
      id: number,
    },
    status: string,
  }[],
  name: string,
  phase: string,
  proxies: MySQLClusterInfos['masters'],
  region: string,
  repeaters: string[],
  slaves: MySQLClusterInfos['masters'],
  status: string,
  time_zone: string,
  updater: string
}
