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

import type { AuthorizePreCheckData } from '@services/types/permission';

import { TicketTypes } from '@common/const';

import type { IHostTableData } from '@components/cluster-common/big-data-host-table/HdfsHostTable.vue';

import type { HostDetails, HostSubmitParams } from './ip';

/**
 * 部署地域信息
 */
export interface CitiyItem {
  city_code: string,
  city_name: string,
  inventory: number,
  inventory_tag: string
}

/**
 * 机型信息
 */
export interface HostSpec {
  cpu: string,
  mem: string,
  spec: string,
  type: string,
}

/**
 * redis 容量信息
 */
export interface CapSepcs {
  group_num: number,
  maxmemory: number,
  shard_num: number,
  spec: string,
  total_memory: number
  cap_key: string,
  selected: boolean
  max_disk: number,
  total_disk: string,
}

/**
 * 获取 redis 容量信息参数
 */
export interface CapSpecsParams {
  nodes: {
    master: Array<HostSubmitParams>,
    slave: Array<HostSubmitParams>
  },
  ip_source: string
  cluster_type: string
}

/**
 * 获取单据列表过滤参数
 */
export interface GetTicketParams {
  bk_biz_id?: number,
  ticket_type?: string,
  status?: string,
  limit?: number,
  offset?: number,
}

/**
 * 单据列表项
 */
export interface TicketItem {
  db_app_abbr: string,
  bk_biz_id: number,
  bk_biz_name: string,
  cost_time: number,
  create_at: string,
  creator: string,
  details: any,
  id: number,
  remark: string,
  status: string,
  status_display: string,
  ticket_type: string,
  ticket_type_display: string,
  update_at: string,
  updater: string,
  is_reviewed: boolean,
  related_object: {
    title: string,
    objects: string[]
  }
}

/**
 * 单据列表返回结果
 */
export interface TicketResult {
  count: number,
  next: string,
  previous: string,
  results: TicketItem[]
}

/**
 * 单据详情
 */
export interface TicketDetails<T> {
  id: number,
  creator: string,
  create_at: string,
  updater: string,
  update_at: string,
  ticket_type: string,
  status: string,
  remark: string,
  details: T,
  ticket_type_display: string,
  status_display: string,
  cost_time: number,
  bk_biz_name: string,
  db_app_abbr: string,
  bk_biz_id: number
}

/**
 * mysql - 单据详情
 */
export interface TicketDetailsMySQL {
  city_code: string,
  city_name: string,
  spec: string,
  db_module_id: number,
  cluster_count: number,
  inst_num: number,
  domains: [
    {
      key: string,
      master: string,
      slave?: string,
    }
  ],
  db_module_name: string,
  start_mysql_port: number,
  spec_display: string,
  db_version: string,
  charset: string,
  start_proxy_port: number,
  nodes: {
    proxy: Array<{ ip: string, bk_host_id: number, bk_cloud_id: number }>,
    backend: Array<{ ip: string, bk_host_id: number, bk_cloud_id: number }>
  }
}

/**
 * redis - 单据详情
 */
export interface TicketDetailsRedis {
  db_app_abbr: string,
  cap_key: string,
  city_code: string,
  city_name: string,
  cluster_alias: string,
  cluster_name: string,
  cluster_type: string,
  db_version: string,
  ip_source: string,
  cap_spec: string,
  nodes: {
    proxy: HostDetails[],
    master: HostDetails[],
    slave: HostDetails[],
  }
  proxy_port: number,
}

/**
 * 单据流程信息
 */
export interface FlowItem {
  id: number,
  status: 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'SKIPPED' | 'REVOKED',
  url: string,
  start_time: string,
  end_time: string,
  flow_type: string,
  flow_type_display: string,
  flow_obj_id: string,
  ticket: number,
  summary: string,
  cost_time: number,
  err_code: number,
  err_msg: string,
  todos: FlowItemTodo[],
  details: {
    ticket_data: MySQLImportSQLFileDetails,
  },
}

/**
 * 单据流程待办信息
 */
export interface FlowItemTodo {
  context: { flow_id: number, ticket_id: number },
  flow_id: number,
  ticket_id: number,
  cost_time: number,
  done_at: null | string,
  done_by: string,
  flow: number,
  id: number,
  name: string,
  operators: string[],
  status: 'TODO' | 'RUNNING' | 'DONE_SUCCESS' | 'DONE_FAILED',
  ticket: number,
  type: 'APPROVE' | 'INNER_APPROVE',
  url: string
}

/**
 *  创建业务英文缩写参数
 */
export interface CreateAbbrParams {
  db_app_abbr: string
}

/**
 * 创建模块参数
 */
export interface CreateModuleParams {
  db_module_name: string,
  cluster_type: string
}

/**
 * 创建模块返回结果
 */
export interface CreateModuleResult {
  db_module_id: number
  db_module_name: string,
  cluster_type: string,
  bk_biz_id: number,
  bk_set_id: number
  bk_modules: { bk_module_name: string, bk_module_id: string }[]
  name: string,
}

/**
 * 保存模块部署配置
 */
export interface CreateModuleDeployInfo {
  bk_biz_id: number,
  conf_items: ConfItems[],
  version: string,
  meta_cluster_type: string,
  level_name: string,
  level_value: number,
  conf_type: string,
}

export interface ConfItems {
  conf_name: string,
  conf_value: string,
  op_type: string
}

/**
 * 单据类型
 */
export interface TicketType {
  key: string,
  value: string,
}

/**
 * 获取单据详情节点列表参数
 */
export interface TicketNodesParams {
  bk_biz_id: number,
  id: number,
  role: string,
  keyword?: string
}

/**
 * redis-提取key | 删除key 详情
 */
export interface RedisKeysDetails {
  delete_type: string,
  rules: {
    black_regex: string,
    cluster_id: number,
    domain: string,
    path: string,
    total_size: string,
    white_regex: string,
    create_at: string,
  }[],
  clusters: clustersItems,
}

/**
 * mysql-查询账号参数
 */
export interface MysqlQueryAccountParams {
  user: string,
  access_dbs: string[],
}
/**
 * mysql-授权详情
 */
export interface MysqlAuthorizationDetails {
  authorize_uid: string,
  authorize_data: AuthorizePreCheckData,
  excel_url: string,
}

/**
 * es - 单据详情
 */
export interface TicketDetailsES {
  db_app_abbr: string,
  city_code: string,
  cluster_alias: string,
  cluster_name: string,
  db_version: string,
  http_port: number,
  ip_source: string,
  nodes: {
    client: IHostTableData[],
    master: IHostTableData[],
    hot: IHostTableData[],
    cold: IHostTableData[],
  },
}

/**
 * hdfs - 单据详情
 */
export interface TicketDetailsHDFS {
  db_app_abbr: string,
  city_code: string,
  cluster_alias: string,
  cluster_name: string,
  db_version: string,
  ip_source: string,
  nodes: {
    datanode: IHostTableData[],
    namenode: IHostTableData[],
    zookeeper: IHostTableData[],
  },
}

/**
 * kafka - 单据详情
 */
export interface TicketDetailsKafka {
  db_app_abbr: string,
  city_code: string,
  cluster_alias: string,
  cluster_name: string,
  db_version: string,
  ip_source: string,
  nodes: {
    broker: IHostTableData[],
    zookeeper: IHostTableData[],
  },
  partition_num: number,
  port: number,
  replication_num: number,
  retention_hours: number,
}

/**
 * 节点类型
 */
export interface NodesType {
  datanode: IHostTableData[],
  hot: IHostTableData[],
  cold: IHostTableData[],
  master: IHostTableData[],
  client: IHostTableData[],
  namenode: IHostTableData[],
  zookeeper: IHostTableData[],
  broker: IHostTableData[],
  proxy: IHostTableData[],
  slave: IHostTableData[],
}

/**
 * Redis、大数据启停删单据
 */
export interface ClusterOperationDetails {
  clusters: clustersItems
  cluster_id: number,
}

/**
 * MySQL 权限克隆详情
 */
export interface MySQLCloneDetails {
  clone_type: string,
  clone_uid: string,
  clone_data: {
    source: string,
    target: string[],
    module: string,
    cluster_domain: '',
  }[],
}

/**
 * MySQL Slave详情
 */
export interface MySQLSlaveDetails {
  clusters: clustersItems,
  infos: {
    backup_source: string,
    cluster_ids: number[],
    cluster_id: number,
    new_slave: MysqlIpItem,
    slave: MysqlIpItem,
  }[],
}

/**
 * MySQL 重命名
 */
export interface MySQLRenameDetails {
  clusters: clustersItems,
  infos: {
    cluster_id: number,
    force: boolean,
    from_database: string,
    to_database: string,
  }[],
}

/**
 * 大数据实例重启
 */
export interface BigDataRebootDetails {
  clusters: clustersItems,
  cluster_id: number,
  instance_list: {
    bk_cloud_id: number,
    bk_host_id: number,
    instance_id: number,
    instance_name: string,
    ip: string,
    port: number,
  }[],
}

/**
 * MySQL 替换 PROXY
 */
export interface MySQLProxySwitchDetails {
  clusters: clustersItems,
  force: boolean,
  infos: {
    cluster_ids: number[],
    origin_proxy: MysqlIpItem,
    target_proxy: MysqlIpItem,
  }[],
}

/**
 * clusters参数
 */
export interface clustersItems {
  [key: number]: {
    alias: string,
    bk_biz_id: number,
    bk_cloud_id: number,
    cluster_type: string,
    cluster_type_name: string,
    creator: string,
    db_module_id: number,
    id: number,
    immute_domain: string,
    major_version: string,
    name: string,
    phase: string,
    region: string,
    status: string,
    time_zone: string,
    updater: string,
  },
}

/**
 * MySQL 库表备份
 */
export interface MySQLTableBackupDetails {
  clusters: clustersItems,
  infos: {
    backup_on: string,
    cluster_id: number,
    db_patterns: [],
    ignore_dbs: [],
    ignore_tables: [],
    table_patterns: [],
    force: boolean,
  }[],
}

/**
 * MySQL 高可用清档
 */
export interface MySQLHATruncateDetails {
  clusters: clustersItems,
  infos: {
    cluster_id: number,
    db_patterns: [],
    ignore_dbs: [],
    ignore_tables: [],
    table_patterns: [],
    force: boolean,
    truncate_data_type: string,
  }[],
}

export interface MysqlIpItem {
  bk_biz_id: number,
  bk_cloud_id: number,
  bk_host_id: number,
  ip: string,
  port?: number,
}

/**
 * MySQL 克隆主从
 */
export interface MySQLMigrateDetails {
  clusters: clustersItems,
  infos: {
    cluster_ids: number[],
    new_master: MysqlIpItem,
    new_slave: MysqlIpItem,
  }[],
}

/**
 * MySQL 主从互换
 */
export interface MySQLMasterSlaveDetails {
  clusters: clustersItems,
  infos: {
    cluster_ids: number[],
    master_ip: MysqlIpItem,
    slave_ip: MysqlIpItem,
  }[],
}

/**
 * MySQL 新增 Proxy
 */
export interface MySQLProxyAddDetails {
  clusters: clustersItems,
  infos: {
    cluster_ids: number[],
    new_proxy: MysqlIpItem,
  }[],
}

/**
 * MySQL 主故障切换
 */
export interface MySQLMasterFailDetails {
  clusters: clustersItems,
  infos: {
    cluster_ids: number[],
    master_ip: MysqlIpItem,
    slave_ip: MysqlIpItem,
  }[],
}

/**
 * MySQL SQL变更执行
 */
export interface MySQLImportSQLFileDetails {
  uid: string,
  path: string,
  backup: {
    backup_on: string,
    db_patterns: [],
    table_patterns: [],
  }[],
  charset: string,
  root_id: string,
  bk_biz_id: number,
  created_by: string,
  cluster_ids: number[],
  clusters: clustersItems,
  ticket_mode: {
    mode: string,
    trigger_time: string,
  },
  ticket_type: string,
  execute_objects: {
    dbnames: [],
    sql_file: string,
    ignore_dbnames: []
  }[],
  execute_db_infos: {
    dbnames: [],
    ignore_dbnames: []
  }[],
  execute_sql_files: [],
  import_mode: string,
  semantic_node_id: string,
}

/**
 * MySQL 闪回
 */
export interface MySQLFlashback {
  infos: {
    cluster_id: number,
    databases: [],
    databases_ignore: [],
    end_time: string,
    mysqlbinlog_rollback: string,
    recored_file: string,
    start_time: string,
    tables: [],
    tables_ignore: []
  }[],
}

/**
 * MySql 定点回档
 */
export interface MySQLRollbackDetails {
  infos: {
    backup_source: string,
    backupid: string,
    cluster_id: number,
    databases: string[],
    databases_ignore: string[],
    rollback_ip: string,
    rollback_time: string,
    tables: string[],
    tables_ignore: string[],
    backupinfo: {
      backup_id: string,
      mysql_host: string,
      mysql_port: number,
      mysql_role: string,
      backup_time: string,
      backup_type: string,
      master_host: string,
      master_port: number
    },
  }[],
}

/**
 * MySQL SLAVE重建
 */
export interface MySQLRestoreSlaveDetails {
  clusters: clustersItems,
  infos: {
    backup_source: string,
    cluster_ids: number[],
    new_slave: MysqlIpItem,
    old_slave: MysqlIpItem,
  }[],
}

/**
 * MySQL 全库备份
 */
export interface MySQLFullBackupDetails {
  clusters: clustersItems,
  infos: {
    backup_type: string,
    cluster_ids: number[],
    file_tag: string,
    online: boolean,
  }
}

/**
 * MySQL 校验
 */
export interface MySQLChecksumDetails {
  clusters: clustersItems,
  data_repair: {
    is_repair: boolean,
    mode: string,
  }
  infos: {
    cluster_id: number,
    db_patterns: string[],
    ignore_dbs: string[],
    ignore_tables: string[],
    master: {
      id: number,
      ip: string,
      port: number,
    },
    slaves: {
      id: number,
      ip: string,
      port: number,
    }[],
    table_patterns: string[],
  }[],
  is_sync_non_innodb: boolean,
  runtime_hour: number,
  timing: string,
}

/**
 * 变更事件项
 */
export interface ClusterOperateRecord {
  create_at: string,
  ticket_id: number,
  op_type: string,
  op_status: 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'REVOKED'
}

/**
 * MySQL 启停删
 */
export interface MySQLOperationDetails {
  clusters: clustersItems
  cluster_ids: number[],
  force: boolean,
}

/**
 * 大数据替换
 */
export interface BigDataReplaceDetails {
  clusters: clustersItems
  ip_source: string,
  cluster_id: number,
  new_nodes: NodesType,
  old_nodes: NodesType,
}

/**
 * 大数据扩缩容
 */
export interface BigDataCapacityDetails {
  clusters: clustersItems
  cluster_id: number,
  nodes: NodesType,
}

// Redis 提交单据
export interface SubmitTicket<T extends TicketTypes, U extends Array<unknown>> {
  bk_biz_id: number;
  ticket_type: T;
  details: {
    ip_source: 'resource_pool',
    infos: U
  }
}
