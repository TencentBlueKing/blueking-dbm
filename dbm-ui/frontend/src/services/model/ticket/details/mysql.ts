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
import type { AccountRule, AccountRulePrivilege, AuthorizePreCheckData } from '@services/types/permission';

import type { DetailBase, DetailClusters, SpecInfo } from './common';

export interface MysqlIpItem extends DetailBase {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_host_id: number;
  ip: string;
  port?: number;
}

/**
 * mysql-授权详情
 */
export interface MysqlAuthorizationDetails extends DetailBase {
  // 普通授权
  authorize_data: AuthorizePreCheckData;
  authorize_data_list: AuthorizePreCheckData[];
  // 插件授权
  authorize_plugin_infos: AuthorizePreCheckData[];
  authorize_uid: string;
  // 批量导入
  excel_url: string;
}

export interface MySQLForceImportSQLFileExecuteSqlFiles {
  raw_file_name: string;
  sql_content: string;
  sql_path: string;
}
/**
 * MySQL SQL变更执行
 */
export interface MySQLImportSQLFileDetails extends DetailBase {
  backup: {
    backup_on: string;
    db_patterns: [];
    table_patterns: [];
  }[];
  bk_biz_id: number;
  charset: string;
  cluster_ids: number[];
  clusters: DetailClusters;
  created_by: string;
  dump_file_path?: string;
  execute_db_infos: {
    dbnames: [];
    ignore_dbnames: [];
  }[];
  execute_objects: {
    dbnames: [];
    ignore_dbnames: [];
    sql_files: string[];
  }[];
  execute_sql_files: string[] | MySQLForceImportSQLFileExecuteSqlFiles[];
  grammar_check_info: Record<
    string,
    {
      highrisk_warnings: {
        command_type: string;
        line: number;
        sqltext: string;
        warn_info: string;
      }[];
    }
  >;
  import_mode: string;
  path: string;
  root_id: string;
  semantic_node_id: string;
  ticket_mode: {
    mode: string;
    trigger_time: string;
  };
  ticket_type: string;
  uid: string;
}

/**
 * MySQL 校验
 */
export interface MySQLChecksumDetails extends DetailBase {
  clusters: DetailClusters;
  data_repair: {
    is_repair: boolean;
    mode: string;
  };
  infos: {
    cluster_id: number;
    db_patterns: string[];
    ignore_dbs: string[];
    ignore_tables: string[];
    master: {
      id: number;
      ip: string;
      port: number;
    };
    slaves: {
      id: number;
      ip: string;
      port: number;
    }[];
    table_patterns: string[];
  }[];
  is_sync_non_innodb: boolean;
  runtime_hour: number;
  timing: string;
}

/**
 * MySQL 权限克隆详情
 */
export interface MySQLCloneDetails extends DetailBase {
  clone_data: {
    bk_cloud_id: number;
    cluster_domain?: string;
    module: string;
    source: string;
    target: string[];
  }[];
  clone_type: string;
  clone_uid: string;
}

/**
 * MySQL DB实例克隆详情
 */
export interface MySQLInstanceCloneDetails extends DetailBase {
  clone_data: {
    bk_cloud_id: number;
    cluster_domain: string;
    cluster_id: number;
    module: string;
    source: string;
    target: string;
  }[];
  clone_type: string;
  clone_uid: string;
}

/**
 * MySQL 启停删
 */
export interface MySQLOperationDetails extends DetailBase {
  cluster_ids: number[];
  clusters: DetailClusters;
  force: boolean;
}

/**
 * mysql - 单据详情
 */
export interface MySQLDetails extends DetailBase {
  bk_cloud_id: number;
  charset: string;
  city_code: string;
  city_name: string;
  cluster_count: number;
  db_module_id: number;
  db_module_name: string;
  db_version: string;
  disaster_tolerance_level: string;
  domains: {
    key: string;
    master: string;
    slave?: string;
  }[];
  inst_num: number;
  ip_source: string;
  nodes: {
    backend: { bk_cloud_id: number; bk_host_id: number; ip: string }[];
    proxy: { bk_cloud_id: number; bk_host_id: number; ip: string }[];
  };
  resource_spec: {
    backend: SpecInfo;
    backend_group: SpecInfo;
    proxy: SpecInfo;
  };
  spec: string;
  spec_display: string;
  start_mysql_port: number;
  start_proxy_port: number;
}

export interface DumperInstallDetails extends DetailBase {
  add_type: string;
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    db_module_id: number;
    dumper_id: number;
    kafka_pwd: string;
    l5_cmdid: number;
    l5_modid: number;
    protocol_type: string;
    target_address: string;
    target_port: number;
  }[];
  name: string;
  repl_tables: string[];
}

export interface DumperNodeStatusUpdateDetails extends DetailBase {
  dumper_instance_ids: number[];
  dumpers: {
    [key: string]: {
      add_type: string;
      bk_biz_id: number;
      bk_cloud_id: number;
      cluster_id: number;
      creator: string;
      dumper_id: string;
      id: number;
      ip: string;
      listen_port: number;
      need_transfer: boolean;
      phase: string;
      proc_type: string;
      protocol_type: string;
      source_cluster: {
        bk_cloud_id: number;
        cluster_type: string;
        id: number;
        immute_domain: string;
        major_version: string;
        master_ip: string;
        master_port: number;
        name: string;
        region: string;
      };
      target_address: string;
      target_port: number;
      updater: string;
      version: string;
    };
  };
}

export interface DumperSwitchNodeDetails extends DetailBase {
  clusters: DetailClusters;
  infos: Array<{
    cluster_id: number;
    switch_instances: Array<{
      host: string;
      port: number;
      repl_binlog_file: string;
      repl_binlog_pos: number;
    }>;
  }>;
  is_safe: boolean;
}

/**
 * MySQL 闪回
 */
export interface MySQLFlashback extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    databases: [];
    databases_ignore: [];
    end_time: string;
    mysqlbinlog_rollback: string;
    recored_file: string;
    start_time: string;
    tables: [];
    tables_ignore: [];
  }[];
}

/**
 * MySQL 全库备份
 */
export interface MySQLFullBackupDetails extends DetailBase {
  // 新版协议
  backup_type: string;
  clusters: DetailClusters;
  file_tag: string;
  infos:
    | {
        // 旧版协议
        backup_type: string;
        clusters: {
          backup_local: string;
          cluster_id: number;
        }[];
        file_tag: string;
        online: boolean;
      }
    | {
        // 新版协议
        backup_local: string;
        cluster_id: number;
      }[];
  online: boolean;
}

/**
 * MySQL 主从清档
 */
export interface MySQLHATruncateDetails extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    db_patterns: [];
    force: boolean;
    ignore_dbs: [];
    ignore_tables: [];
    table_patterns: [];
    truncate_data_type: string;
  }[];
}

/**
 * MySQL 主故障切换
 */
export interface MySQLMasterFailDetails extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_ids: number[];
    master_ip: MysqlIpItem;
    slave_ip: MysqlIpItem;
  }[];
  is_check_delay: boolean;
  is_check_process: boolean;
  is_verify_checksum: boolean;
}

/**
 * MySQL 主从互换
 */
export interface MySQLMasterSlaveDetails extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_ids: number[];
    master_ip: MysqlIpItem;
    slave_ip: MysqlIpItem;
  }[];
  is_check_delay: boolean;
  is_check_process: boolean;
  is_verify_checksum: boolean;
}

/**
 * MySQL 克隆主从
 */
export interface MySQLMigrateDetails extends DetailBase {
  backup_source: string;
  clusters: DetailClusters;
  infos: {
    cluster_ids: number[];
    new_master: MysqlIpItem;
    new_slave: MysqlIpItem;
  }[];
  is_safe: boolean;
}

export interface MysqlOpenAreaDetails extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
  config_data: {
    cluster_id: number;
    execute_objects: {
      data_tblist: string[];
      schema_tblist: string[];
      source_db: string;
      target_db: string;
    }[];
  }[];
  config_id: number;
  force: boolean;
  rules_set: {
    account_rules: {
      bk_biz_id: number;
      dbname: string;
    }[];
    cluster_type: string;
    privileges: {
      access_db: string;
      priv: string;
      user: string;
    }[];
    source_ips: string[];
    target_instances: string[];
    user: string;
  }[];
}

/**
 * MySQL 新增 Proxy
 */
export interface MySQLProxyAddDetails extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_ids: number[];
    new_proxy: MysqlIpItem;
  }[];
}

/**
 * MySQL 替换 PROXY
 */
export interface MySQLProxySwitchDetails extends DetailBase {
  clusters: DetailClusters;
  force: boolean;
  infos: {
    cluster_ids: number[];
    display_info: Record<string, unknown>;
    origin_proxy: MysqlIpItem;
    target_proxy: MysqlIpItem;
  }[];
}

/**
 * MySQL 重命名
 */
export interface MySQLRenameDetails extends DetailBase {
  clusters: DetailClusters;
  force: boolean;
  infos: {
    cluster_id: number;
    force: boolean;
    from_database: string;
    to_database: string;
  }[];
}

/**
 * MySQL SLAVE重建
 */
export interface MySQLRestoreSlaveDetails extends DetailBase {
  backup_source: string;
  clusters: DetailClusters;
  infos: {
    cluster_ids: number[];
    new_slave: MysqlIpItem;
    old_slave: MysqlIpItem;
  }[];
}

/**
 * MySQL SLAVE原地重建
 */
export interface MySQLRestoreLocalSlaveDetails extends DetailBase {
  backup_source: string;
  clusters: DetailClusters;
  force: boolean;
  infos: {
    backup_source: string;
    cluster_id: number;
    slave: MysqlIpItem;
  }[];
}

/**
 * MySql 定点回档类型
 */
export enum RollbackClusterTypes {
  BUILD_INTO_EXIST_CLUSTER = 'BUILD_INTO_EXIST_CLUSTER',
  BUILD_INTO_METACLUSTER = 'BUILD_INTO_METACLUSTER',
  BUILD_INTO_NEW_CLUSTER = 'BUILD_INTO_NEW_CLUSTER',
}

/**
 * MySql 定点回档主机信息
 */
export interface RollbackHost {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_host_id: number;
  ip: string;
}

/**
 * MySql 定点回档
 */
export interface MySQLRollbackDetails extends DetailBase {
  clusters: DetailClusters;
  infos: {
    backup_source: string;
    backupinfo: {
      backup_id: string;
      backup_time: string;
      backup_type: string;
      master_host: string;
      master_port: number;
      mysql_host: string;
      mysql_port: number;
      mysql_role: string;
    };
    cluster_id: number;
    databases: string[];
    databases_ignore: string[];
    rollback_host: RollbackHost;
    rollback_time: string;
    rollback_type: string;
    tables: string[];
    tables_ignore: string[];
    target_cluster_id: number;
  }[];
  rollback_cluster_type: RollbackClusterTypes;
}

/**
 * MySQL Slave详情
 */
export interface MySQLSlaveDetails extends DetailBase {
  backup_source: string;
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    cluster_ids: number[];
    new_slave: MysqlIpItem;
    slave: MysqlIpItem;
  }[];
}

/**
 * MySQL 库表备份
 */
export interface MySQLTableBackupDetails extends DetailBase {
  clusters: DetailClusters;
  infos: {
    backup_on: string;
    cluster_id: number;
    db_patterns: string[];
    force: boolean;
    ignore_dbs: string[];
    ignore_tables: string[];
    table_patterns: string[];
  }[];
}

/**
 * MySQL 数据导出
 */
export interface MySQLExportData extends DetailBase {
  charset: string;
  cluster_id: number;
  clusters: DetailClusters;
  databases: string[];
  dump_data: boolean; // 是否导出表数据
  dump_schema: boolean; // 是否导出表结构
  tables: string[];
  tables_ignore: string[];
  where: string;
}

export interface MysqlDataMigrateDetails extends DetailBase {
  clusters: DetailClusters;
  infos: {
    data_schema_grant: string;
    db_list: string;
    source_cluster: number;
    target_clusters: number[];
  }[];
}

/**
 * MySQL Proxy 升级
 */
export interface MySQLProxyUpgradeDetails extends DetailBase {
  clusters: DetailClusters;
  force: boolean;
  infos: {
    cluster_ids: number[];
    display_info: {
      current_version: string;
    };
    pkg_id: string;
  }[];
}

/**
 * MySQL 原地升级
 */
export interface MySQLLocalUpgradeDetails extends DetailBase {
  clusters: DetailClusters;
  force: boolean;
  infos: {
    cluster_ids: number[];
    display_info: {
      charset: string;
      cluster_type: string;
      current_module_name: string;
      current_package: string;
      current_version: string;
      target_package: string;
    };
    pkg_id: number;
  }[];
}

/**
 * MySQL 迁移升级
 */
export interface MySQLMigrateUpgradeDetails extends DetailBase {
  backup_source: string;
  clusters: DetailClusters;
  force: boolean;
  infos: {
    cluster_ids: number[];
    display_info: {
      charset: string;
      current_module_name: string;
      current_package: string;
      current_version: string;
      old_master_slave?: string[];
      target_module_name: string;
      target_package: string;
      target_version: string;
    };
    new_db_module_id: number;
    new_master: MysqlIpItem;
    new_slave: MysqlIpItem;
    pkg_id: string;
    read_only_slaves?: {
      new_slave: MysqlIpItem;
      old_slave: MysqlIpItem;
    }[];
  }[];
  ip_source: string;
}

/**
 * MySQL 权限规则变更
 */
export interface MySQLAccountRuleChangeDetails extends DetailBase {
  access_db: string;
  account_id: number;
  account_type: string;
  action: 'change' | 'delete';
  bk_biz_id: number;
  last_account_rules: {
    userName: string;
  } & AccountRule;
  privilege: AccountRulePrivilege;
  rule_id: number;
}
