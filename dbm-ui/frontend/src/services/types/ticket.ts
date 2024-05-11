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

import type { MySQLImportSQLFileDetails } from '@services/model/ticket/details/mysql';

import { TicketTypes } from '@common/const';

import type { IHostTableData } from '@components/cluster-common/big-data-host-table/HdfsHostTable.vue';

import type { HostSubmitParams } from './ip';

/**
 * 部署地域信息
 */
export interface CitiyItem {
  city_code: string;
  city_name: string;
  inventory: number;
  inventory_tag: string;
}

/**
 * 机型信息
 */
export interface HostSpec {
  cpu: string;
  mem: string;
  spec: string;
  type: string;
}

/**
 * redis 容量信息
 */
export interface CapSepcs {
  group_num: number;
  maxmemory: number;
  shard_num: number;
  spec: string;
  total_memory: number;
  cap_key: string;
  selected: boolean;
  max_disk: number;
  total_disk: string;
}

/**
 * 获取 redis 容量信息参数
 */
export interface CapSpecsParams {
  nodes: {
    master: Array<HostSubmitParams>;
    slave: Array<HostSubmitParams>;
  };
  ip_source: string;
  cluster_type: string;
}

/**
 * 获取单据列表过滤参数
 */
export interface GetTicketParams {
  bk_biz_id?: number;
  ticket_type?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

/**
 * 单据列表项
 */
export interface TicketItem {
  db_app_abbr: string;
  bk_biz_id: number;
  bk_biz_name: string;
  cost_time: number;
  create_at: string;
  creator: string;
  details: any;
  id: number;
  remark: string;
  status: string;
  status_display: string;
  ticket_type: string;
  ticket_type_display: string;
  update_at: string;
  updater: string;
  is_reviewed: boolean;
  related_object: {
    title: string;
    objects: string[];
  };
}

/**
 * 单据列表返回结果
 */
export interface TicketResult {
  count: number;
  next: string;
  previous: string;
  results: TicketItem[];
}

/**
 * 单据详情
 */
export interface TicketDetails<T> {
  [key: string]: number | string | boolean | TicketTypes | T;
  bk_biz_id: number;
  bk_biz_name: string;
  cost_time: number;
  create_at: string;
  creator: string;
  db_app_abbr: string;
  details: T;
  group: string;
  id: number;
  ignore_duplication: boolean;
  is_reviewed: boolean;
  remark: string;
  status: string;
  status_display: string;
  ticket_type: TicketTypes;
  ticket_type_display: string;
  update_at: string;
  updater: string;
}

/**
 * 单据流程信息
 */
export interface FlowItem {
  id: number;
  status: 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'SKIPPED' | 'REVOKED' | 'TERMINATED';
  url: string;
  start_time: string;
  end_time: string;
  flow_type: string;
  flow_type_display: string;
  flow_obj_id: string;
  ticket: number;
  summary: string;
  cost_time: number;
  err_code: number;
  err_msg: string;
  todos: FlowItemTodo[];
  details: {
    ticket_data: MySQLImportSQLFileDetails;
  };
}

/**
 * 单据流程待办信息
 */
export interface FlowItemTodo {
  context: {
    flow_id: number;
    ticket_id: number;
    administrators?: string[];
    user?: string;
  };
  flow_id: number;
  ticket_id: number;
  cost_time: number;
  done_at: null | string;
  done_by: string;
  flow: number;
  id: number;
  name: string;
  operators: string[];
  status: 'TODO' | 'RUNNING' | 'DONE_SUCCESS' | 'DONE_FAILED';
  ticket: number;
  type: 'APPROVE' | 'INNER_APPROVE' | 'RESOURCE_REPLENISH';
  url: string;
}

/**
 *  创建业务英文缩写参数
 */
export interface CreateAbbrParams {
  db_app_abbr: string;
}

/**
 * 创建模块参数
 */
export interface CreateModuleParams {
  db_module_name: string;
  cluster_type: string;
}

/**
 * 创建模块返回结果
 */
export interface CreateModuleResult {
  db_module_id: number;
  db_module_name: string;
  cluster_type: string;
  bk_biz_id: number;
  bk_set_id: number;
  bk_modules: { bk_module_name: string; bk_module_id: string }[];
  name: string;
}

/**
 * 保存模块部署配置
 */
export interface CreateModuleDeployInfo {
  bk_biz_id: number;
  conf_items: ConfItems[];
  version: string;
  meta_cluster_type: string;
  level_name: string;
  level_value: number;
  conf_type: string;
}

export interface ConfItems {
  conf_name: string;
  conf_value: string;
  op_type: string;
}

/**
 * 单据类型
 */
export interface TicketType {
  key: string;
  value: string;
}

/**
 * 获取单据详情节点列表参数
 */
export interface TicketNodesParams {
  bk_biz_id: number;
  id: number;
  role: string;
  keyword?: string;
}

/**
 * mysql-查询账号参数
 */
export interface MysqlQueryAccountParams {
  user: string;
  access_dbs: string[];
}

/**
 * es - 单据详情
 */
export interface TicketDetailsES {
  db_app_abbr: string;
  city_code: string;
  cluster_alias: string;
  cluster_name: string;
  db_version: string;
  http_port: number;
  ip_source: string;
  nodes: {
    client: IHostTableData[];
    master: IHostTableData[];
    hot: IHostTableData[];
    cold: IHostTableData[];
  };
}

/**
 * hdfs - 单据详情
 */
export interface TicketDetailsHDFS {
  db_app_abbr: string;
  city_code: string;
  cluster_alias: string;
  cluster_name: string;
  db_version: string;
  ip_source: string;
  nodes: {
    datanode: IHostTableData[];
    namenode: IHostTableData[];
    zookeeper: IHostTableData[];
  };
}

/**
 * kafka - 单据详情
 */
export interface TicketDetailsKafka {
  db_app_abbr: string;
  city_code: string;
  cluster_alias: string;
  cluster_name: string;
  db_version: string;
  ip_source: string;
  nodes: {
    broker: IHostTableData[];
    zookeeper: IHostTableData[];
  };
  partition_num: number;
  port: number;
  replication_num: number;
  retention_hours: number;
}

/**
 * 节点类型
 */
export interface NodesType {
  datanode: IHostTableData[];
  hot: IHostTableData[];
  cold: IHostTableData[];
  master: IHostTableData[];
  client: IHostTableData[];
  namenode: IHostTableData[];
  zookeeper: IHostTableData[];
  broker: IHostTableData[];
  proxy: IHostTableData[];
  slave: IHostTableData[];
}

/**
 * Redis、大数据启停删单据
 */
export interface ClusterOperationDetails {
  clusters: clustersItems;
  cluster_id: number;
}

/**
 * 大数据实例重启
 */
export interface BigDataRebootDetails {
  clusters: clustersItems;
  cluster_id: number;
  instance_list: {
    bk_cloud_id: number;
    bk_host_id: number;
    instance_id: number;
    instance_name: string;
    ip: string;
    port: number;
  }[];
}

/**
 * clusters参数
 */
export interface clustersItems {
  [key: number]: {
    alias: string;
    bk_biz_id: number;
    bk_cloud_id: number;
    cluster_type: string;
    cluster_type_name: string;
    creator: string;
    db_module_id: number;
    id: number;
    immute_domain: string;
    major_version: string;
    name: string;
    phase: string;
    region: string;
    status: string;
    time_zone: string;
    updater: string;
  };
}

/**
 * 变更事件项
 */
export interface ClusterOperateRecord {
  create_at: string;
  ticket_id: number;
  op_type: string;
  op_status: 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'REVOKED';
}

/**
 * 大数据替换
 */
export interface BigDataReplaceDetails {
  clusters: clustersItems;
  ip_source: string;
  cluster_id: number;
  new_nodes: NodesType;
  old_nodes: NodesType;
}

/**
 * 大数据扩缩容
 */
export interface BigDataCapacityDetails {
  clusters: clustersItems;
  cluster_id: number;
  ip_source: 'manual_input' | 'resource_pool';
  nodes: NodesType;
  resource_spec: {
    [key: string]: {
      count: number;
      instance_num?: number;
      spec_id: number;
    };
  };
  ext_info: {
    [key: string]: {
      host_list: {
        alive: number;
        disk: number;
      }[];
      total_hosts: number;
      total_disk: number;
      target_disk: number;
      expansion_disk: number;
      shrink_disk: number;
    };
  };
}

// Redis 提交单据
export interface SubmitTicket<T extends TicketTypes, U extends Array<unknown>> {
  bk_biz_id: number;
  ticket_type: T;
  details: {
    ip_source?: 'resource_pool';
    infos: U;
  };
}

export interface SpecInfo {
  spec_id: number;
  spec_name: string;
  count: number;
  cpu: {
    max: number;
    min: number;
  };
  mem: {
    max: number;
    min: number;
  };
  storage_spec: {
    mount_point: string;
    size: number;
    type: string;
  }[];
}

/**
 * redis 版本升级
 */
export interface RedisVersionUpgrade {
  clusters: clustersItems;
  infos: {
    cluster_id: number;
    current_versions: string[];
    node_type: string;
    target_version: string;
  }[];
}
