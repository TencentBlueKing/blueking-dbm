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
  bk_biz_id: number,
  bk_biz_name: string,
  cost_time: number,
  create_at: string,
  creator: string,
  db_app_abbr: string,
  details: T,
  group: string,
  id: number,
  ignore_duplication: boolean,
  is_reviewed: boolean,
  remark: string,
  status: string,
  status_display: string,
  ticket_type: TicketTypes,
  ticket_type_display: string,
  update_at: string,
  updater: string,
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
  context: {
    flow_id: number,
    ticket_id: number,
    administrators?: string[],
    user?: string
  },
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
  type: 'APPROVE' | 'INNER_APPROVE' | 'RESOURCE_REPLENISH',
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
    ip_source?: 'resource_pool',
    infos: U
  }
}

interface SpecInfo {
  spec_id: number,
  spec_name: string,
  count: number,
  cpu: {
    max: number,
    min: number
  };
  mem: {
    max: number,
    min: number
  };
  storage_spec: {
    mount_point: string,
    size: number,
    type: string,
  }[];
}

/**
 * mysql - 单据详情
 */
export interface MySQLDetails {
  city_code: string,
  city_name: string,
  cluster_count: number,
  charset: string,
  db_module_name: string,
  db_module_id: number,
  db_version: string,
  ip_source: string,
  inst_num: number,
  start_mysql_port: number,
  spec_display: string,
  start_proxy_port: number,
  spec: string,
  domains: {
    key: string,
    master: string,
    slave?: string,
  }[],
  nodes: {
    proxy: { ip: string, bk_host_id: number, bk_cloud_id: number }[],
    backend: { ip: string, bk_host_id: number, bk_cloud_id: number }[]
  }
  resource_spec: {
    proxy: SpecInfo,
    backend: SpecInfo,
    single: SpecInfo,
  },
}

// redis 整机替换
export interface RedisDBReplaceDetails {
  ip_source: 'resource_pool',
  infos: {
    cluster_id: number,
    bk_cloud_id: number,
    proxy: {
      ip: string,
      spec_id: number
    }[],
    redis_master: {
      ip: string,
      spec_id: number
    }[],
    redis_slave: {
      ip: string,
      spec_id: number
    }[],
  }[],
}

// redis 接入层扩容
export interface RedisProxyScaleUpDetails {
  ip_source: 'resource_pool',
  infos: {
    cluster_id: number,
    bk_cloud_id: number,
    target_proxy_count: number,
    resource_spec: {
      proxy: {
        spec_id: number,
        count: number,
      },
    },
  }[]
}

// redis 接入层缩容
export interface RedisProxyScaleDownDetails {
  ip_source: 'resource_pool',
  infos: {
    cluster_id: number,
    target_proxy_count: number,
    online_switch_type: 'user_confirm' | 'no_confirm',
  }[]
}


// redis 集群容量变更
export interface RedisScaleUpDownDetails {
  ip_source: 'resource_pool',
  infos: {
    cluster_id: number,
    bk_cloud_id: number,
    db_version: string,
    shard_num: number,
    group_num: number,
    online_switch_type: 'user_confirm' | 'no_confirm',
    resource_spec: {
      backend_group: {
        spec_id: number,
        count: number, // 机器组数
        affinity: 'CROS_SUBZONE', // SAME_SUBZONE_CROSS_SWTICH: 同城同subzone跨交换机跨机架 | SAME_SUBZONE: 同城同subzone | CROS_SUBZONE：同城跨subzone | NONE: 无需亲和性处理
      },
    },
  }[]
}

// redis 定点构造
export interface RedisDataStructrue {
  ip_source: 'resource_pool',
  infos: {
    cluster_id: number,
    bk_cloud_id: number,
    master_instances: string[],
    recovery_time_point: string,
    resource_spec: {
      redis: {
        spec_id: number,
        count: number,
      },
    },
  }[]
}

// redis 主故障切换
export interface RedisMasterSlaveSwitchDetails {
  force: boolean,
  infos: {
    cluster_id: number,
    online_switch_type: 'user_confirm' | 'no_confirm',
    pairs: {
      redis_master: string,
      redis_slave: string
    }[]
    ,
  }[]
}

// redis 新建从库
export interface RedisAddSlaveDetails {
  ip_source: 'resource_pool',
  infos: {
    cluster_id: number,
    bk_cloud_id: number,
    pairs: {
      redis_master: {
        ip: string,
        bk_cloud_id: number,
        bk_host_id: number,
      },
      redis_slave: {
        spec_id: number,
        count: number,
      },
    }[]
  }[]
}

// redis 集群分片变更
export interface RedisClusterShardUpdateDetails {
  data_check_repair_setting: {
    // type值为:
    // - data_check_and_repair: 数据校验并修复
    // - data_check_only: 仅进行数据校验，不进行修复
    // - no_check_no_repair: 不校验不修复
    type: 'data_check_and_repair' | 'data_check_only' | 'no_check_no_repair',
    // execution_frequency 执行频次
    execution_frequency: '',
  },
  ip_source: 'resource_pool',
  infos: {
    src_cluster: string,
    current_shard_num: number,
    current_spec_id: string,
    cluster_shard_num: number,
    db_version: string,
    online_switch_type: 'user_confirm',
    resource_spec: {
      proxy: {
        spec_id: number,
        count: number,
        affinity: 'CROS_SUBZONE',
      },
      backend_group: {
        spec_id: number,
        count: number, // 机器组数
        affinity: 'CROS_SUBZONE',
      },
    },
  }[]
}

// redis 集群类型变更
export interface RedisClusterTypeUpdateDetails extends RedisClusterShardUpdateDetails {
  infos: {
    current_cluster_type: string,
    target_cluster_type: string,
    src_cluster: string,
    current_shard_num: number,
    current_spec_id: string,
    cluster_shard_num: number,
    db_version: string,
    online_switch_type: 'user_confirm',
    resource_spec: {
      proxy: {
        spec_id: number,
        count: number,
        affinity: 'CROS_SUBZONE',
      },
      backend_group: {
        spec_id: number,
        count: number, // 机器组数
        affinity: 'CROS_SUBZONE',
      },
    },
  }[]
}

// redis 以构造实例恢复
export interface RedisRollbackDataCopyDetails {
  //  dts 复制类型: 回档临时实例数据回写
  dts_copy_type: 'copy_from_rollback_instance',
  //  write_mode值为:
  //  - delete_and_write_to_redis 先删除同名redis key, 再执行写入 (如: del $key + hset $key)
  //  - keep_and_append_to_redis 保留同名redis key,追加写入
  //  - flushall_and_write_to_redis 先清空目标集群所有数据,在写入
  write_mode: 'delete_and_write_to_redis' | 'keep_and_append_to_redis' | 'flushall_and_write_to_redis',
  infos: {
    src_cluster: string, // 构造产物访问入口
    dst_cluster: string,
    key_white_regex: string, // 包含key
    key_black_regex: string, // 排除key
    recovery_time_point: string, // 构造到指定时间
  }[]
}

// redis 构造销毁
export interface RedisStructureDeleteDetails {
  infos: {
    related_rollback_bill_id: number,
    prod_cluster: string,
    bk_cloud_id: number,
  }[]
}

// redis 数据复制
export interface RedisDataCopyDetails {
  dts_copy_type: 'one_app_diff_cluster' | 'diff_app_diff_cluster' | 'copy_to_other_system' | 'user_built_to_dbm',
  // write_mode值为:
  // - delete_and_write_to_redis 先删除同名redis key, 在执行写入 (如: del $key + hset $key)
  // - keep_and_append_to_redis 保留同名redis key,追加写入
  // - flushall_and_write_to_redis 先清空目标集群所有数据,在写入
  write_mode: 'delete_and_write_to_redis' | 'keep_and_append_to_redis' | 'flushall_and_write_to_redis',
  //  同步断开设置
  sync_disconnect_setting: {
    // type 值为:
    // - auto_disconnect_after_replication: 数据复制完成后自动断开同步关系
    // - keep_sync_with_reminder: 数据复制完成后保持同步关系，定时发送断开同步提醒
    type: 'auto_disconnect_after_replication' | 'keep_sync_with_reminder',
    reminder_frequency: 'once_daily' | 'once_weekly',
  },
  data_check_repair_setting: {
    // type值为:
    // - data_check_and_repair: 数据校验并修复
    // - data_check_only: 仅进行数据校验，不进行修复
    // - no_check_no_repair: 不校验不修复
    type: 'data_check_and_repair' | 'data_check_only' | 'no_check_no_repair',
    //  execution_frequency 执行频次
    execution_frequency: 'once_after_replication' | 'once_every_three_days' | 'once_weekly',
  },
  infos: {
    src_cluster: string,
    dst_cluster: string,
    key_white_regex: string, // 包含key
    key_black_regex: string, // 排除key
    src_cluster_type: 'RedisInstance' | 'RedisCluster', //  RedisInstance主从版,RedisCluster集群版
    dst_bk_biz_id: number,
  }[]
}

// redis 数据校验与修复
export interface RedisDataCheckAndRepairDetails {
  // execute_mode 执行模式
  // - auto_execution 自动执行
  // - scheduled_execution 定时执行
  execute_mode: 'auto_execution' | 'scheduled_execution',
  specified_execution_time: string, //  定时执行,指定执行时间
  check_stop_time: string, //  校验终止时间,
  keep_check_and_repair: boolean, // 是否一直保持校验
  data_repair_enabled: boolean, //  是否修复数据
  repair_mode: 'auto_repair' | 'manual_confirm',
  infos: [
    {
      bill_id: number, // 关联的(数据复制)单据ID
      src_cluster: string, // 源集群,来自于数据复制记录
      src_instances: string[], //  源实例列表
      dst_cluster: string, // 目的集群,来自于数据复制记录
      key_white_regex: string, // 包含key
      key_black_regex: string, // 排除key
    },
  ],
}

// Spider Checksum
export interface SpiderCheckSumDetails {
  data_repair: {
    is_repair: boolean,
    mode: 'timer' | 'manual',
  }
  is_sync_non_innodb: true,
  timing: string,
  runtime_hour: number,
  infos: {
    cluster_id: number,
    checksum_scope: 'partial' | 'all',
    backup_infos: {
      master: string,
      slave: string,
      db_patterns: string[],
      ignore_dbs: string[],
      table_patterns: string[],
      ignore_tables: string[],
    }[]
  }[]
}

// Spider slave集群添加
export interface SpiderSlaveApplyDetails {
  ip_source: 'manual_input',
  infos: {
    cluster_id: number,
    resource_spec: {
      spider_slave_ip_list: {
        spec_id: number,
        count: number
      }
    }
  }[]
}

// Spider 临时节点添加
export interface SpiderMNTApplyDetails {
  infos: {
    cluster_id: number,
    bk_cloud_id: number,
    spider_ip_list: {
      ip: string
      bk_cloud_id: number,
      bk_host_id: number,
    }[],
    immutable_domain: string,
  }[]
}

// Spider 集群下架
export interface SpiderDestroyDetails {
  force: boolean, // 实例强制下架，默认先给false
  cluster_ids: number[], // 待下架的id 列表
}

// Spider 集群启动
export interface SpiderEnableDetails {
  is_only_add_slave_domain: boolean, // 只启用只读集群的话, 这个参数为true
  cluster_ids: number[], // 待下架的id 列表
}

// Spider 集群禁用
export interface SpiderDisableDetails {
  cluster_ids: number[], // 待禁用的id 列表
}

// Spider Tendbcluster 重命名
export interface SpiderRenameDatabaseDetails {
  infos: {
    cluster_id: number,
    from_database: string,
    to_database: string,
    force: boolean,
  }[]
}

// Spider remote 主从互切
export interface SpiderMasterSlaveSwitchDetails {
  force: boolean, // 互切单据就传False，表示安全切换
  is_check_process: boolean,
  is_verify_checksum: boolean,
  is_check_delay: boolean, // 目前互切单据延时属于强制检测，故必须传True， 用户没有选择
  infos: {
    cluster_id: 1,
    switch_tuples: {
      master: {
        ip: string,
        bk_cloud_id: number,
      },
      slave: {
        ip: string,
        bk_cloud_id: number,
      }
    }[]
  }[]
}

// Spider remote主故障切换
export type SpiderMasterFailoverDetails = SpiderMasterSlaveSwitchDetails;

// spider扩容接入层
export interface SpiderAddNodesDeatils {
  ip_source: 'resource_pool',
  infos: {
    cluster_id: number,
    add_spider_role: string,
    resource_spec: {
      spider_ip_list: {
        count: number,
        spec_id: number,
      }
    }
  }[]
}

// Spider TenDBCluster 库表备份
export interface SpiderTableBackupDetails {
  infos: {
    cluster_id: number,
    db_patterns: string[],
    ignore_dbs: string[],
    table_patterns: string[],
    ignore_tables: string[],
    backup_local: string,
  }[]
}

// Spider TenDBCluster 全备单据
export interface SpiderFullBackupDetails {
  infos: {
    backup_type: 'logical' | 'physical',
    file_tag: 'MYSQL_FULL_BACKUP' | 'LONGDAY_DBFILE_3Y',
    clusters: {
      id: 6,
      backup_local: string, // spider_mnt:: 127.0.0.1: 8000
    }[],
  }
}

// spider 缩容接入层
export interface SpiderReduceNodesDetails {
  is_safe: boolean, // 是否做安全检测
  infos: {
    cluster_id: number,
    spider_reduced_to_count: number,
    reduce_spider_role: string,
  }[]
}

// Spider 集群remote节点扩缩容
export interface SpiderNodeRebalanceDetails {
  need_checksum: true,
  trigger_checksum_type: 'now' | 'timer',
  trigger_checksum_time: string,
  infos: {
    bk_cloud_id: number,
    cluster_id: number,
    db_module_id: number,
    cluster_shard_num: number,  // 集群分片数
    remote_shard_num: number, // 单机分片数
    resource_spec: {
      backend_group: {
        spec_id: number,
        count: number,
        affinity: string, // 亲和性要求
      },
    },
  }[]
}

// spider 定点回档
export interface SpiderRollbackDetails {
  cluster_id: number,
  rollbackup_type: 'REMOTE_AND_BACKUPID' | 'REMOTE_AND_TIME',
  rollback_time: string,
  backupinfo: string,
  databases: string[],
  tables: string[],
  databases_ignore: string[],
  tables_ignore: string[],
}

// Spider flashback
export interface SpiderFlashbackDetails {
  infos: {
    cluster_id: number,
    start_time: string,
    end_time: string,
    databases: string[],
    databases_ignore: string[],
    tables: string[],
    tables_ignore: string[],
  }[]
}

// Spider tendbcluster 清档
export interface SpiderTruncateDatabaseDetails {
  infos: {
    cluster_id: number,
    db_patterns: string[],
    ignore_dbs: string[],
    table_patterns: string[],
    ignore_tables: string[],
    truncate_data_type: 'truncate_table' | 'drop_table' | 'drop_database',
    force: boolean,
  }[]
}

// Spider 只读集群下架
export interface SpiderSlaveDestroyDetails {
  is_safe: boolean,
  cluster_ids: number[],
}

// Spider 运维节点下架
export interface SpiderMNTDestroyDetails {
  is_safe: boolean,
  infos: {
    cluster_id: number,
    spider_ip_list: {
      ip: string,
      bk_cloud_id: number
    }[],
  }[]
}

export interface SpiderPartitionManageDetails {
  infos: {
    config_id: string,
    cluster_id: number,
    bk_cloud_id: number,
    immute_domain: string,
    partition_objects: {
      ip: string,
      port: number,
      shard_name: string,
      execute_objects: [
        {
          dblike: string,
          tblike: string,
          config_id: number,
          add_partition: [],
          drop_partition: [],
          init_partition: [
            {
              sql: string,
              need_size: number,
            },
          ],
        },
      ],
    }[]
  }[],
  clusters: {
    [key: number]: {
      id: number,
      name: string,
      alias: string,
      phase: string,
      region: string,
      status: string,
      creator: string,
      updater: string,
      bk_biz_id: number,
      time_zone: string,
      bk_cloud_id: number,
      cluster_type: string,
      db_module_id: number,
      immute_domain: string,
      major_version: string,
      cluster_type_name: string,
    },
  },
}

// redis CLB
export interface RedisCLBDetails {
  cluster_id: number,
  clusters: {
    [key: string]: {
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
      tag: string[],
      time_zone: string,
      updater: string,
    }
  }
}
