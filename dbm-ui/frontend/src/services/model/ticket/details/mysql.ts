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
  authorize_uid: string;
  authorize_data: AuthorizePreCheckData;
  // 批量导入
  excel_url: string;
  authorize_data_list: AuthorizePreCheckData[];
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
  uid: string;
  path: string;
  backup: {
    backup_on: string;
    db_patterns: [];
    table_patterns: [];
  }[];
  charset: string;
  root_id: string;
  bk_biz_id: number;
  created_by: string;
  cluster_ids: number[];
  clusters: DetailClusters;
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
  ticket_mode: {
    mode: string;
    trigger_time: string;
  };
  ticket_type: string;
  execute_objects: {
    dbnames: [];
    ignore_dbnames: [];
    sql_files: string[];
  }[];
  execute_db_infos: {
    dbnames: [];
    ignore_dbnames: [];
  }[];
  execute_sql_files: string[] | MySQLForceImportSQLFileExecuteSqlFiles[];
  import_mode: string;
  semantic_node_id: string;
  dump_file_path?: string;
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
  clone_type: string;
  clone_uid: string;
  clone_data: {
    bk_cloud_id: number;
    source: string;
    target: string[];
    module: string;
    cluster_domain?: string;
  }[];
}

/**
 * MySQL DB实例克隆详情
 */
export interface MySQLInstanceCloneDetails extends DetailBase {
  clone_type: string;
  clone_uid: string;
  clone_data: {
    bk_cloud_id: number;
    source: string;
    target: string;
    module: string;
    cluster_domain: string;
    cluster_id: number;
  }[];
}

/**
 * MySQL 启停删
 */
export interface MySQLOperationDetails extends DetailBase {
  clusters: DetailClusters;
  cluster_ids: number[];
  force: boolean;
}

/**
 * mysql - 单据详情
 */
export interface MySQLDetails extends DetailBase {
  bk_cloud_id: number;
  city_code: string;
  city_name: string;
  cluster_count: number;
  charset: string;
  db_module_name: string;
  db_module_id: number;
  db_version: string;
  disaster_tolerance_level: string;
  ip_source: string;
  inst_num: number;
  start_mysql_port: number;
  spec_display: string;
  start_proxy_port: number;
  spec: string;
  domains: {
    key: string;
    master: string;
    slave?: string;
  }[];
  nodes: {
    proxy: { ip: string; bk_host_id: number; bk_cloud_id: number }[];
    backend: { ip: string; bk_host_id: number; bk_cloud_id: number }[];
  };
  resource_spec: {
    proxy: SpecInfo;
    backend_group: SpecInfo;
    backend: SpecInfo;
  };
}

export interface DumperInstallDetails extends DetailBase {
  name: string;
  infos: {
    l5_cmdid: number;
    l5_modid: number;
    dumper_id: number;
    cluster_id: number;
    db_module_id: number;
    protocol_type: string;
    target_port: number;
    target_address: string;
    kafka_pwd: string;
  }[];
  add_type: string;
  clusters: DetailClusters;
  repl_tables: string[];
}

export interface DumperNodeStatusUpdateDetails extends DetailBase {
  dumpers: {
    [key: string]: {
      id: number;
      ip: string;
      phase: string;
      creator: string;
      updater: string;
      version: string;
      add_type: string;
      bk_biz_id: number;
      dumper_id: string;
      proc_type: string;
      cluster_id: number;
      bk_cloud_id: number;
      listen_port: number;
      target_port: number;
      need_transfer: boolean;
      protocol_type: string;
      source_cluster: {
        id: number;
        name: string;
        region: string;
        master_ip: string;
        bk_cloud_id: number;
        master_port: number;
        cluster_type: string;
        immute_domain: string;
        major_version: string;
      };
      target_address: string;
    };
  };
  dumper_instance_ids: number[];
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
  clusters: DetailClusters;
  infos: {
    backup_type: string;
    clusters: {
      backup_local: string;
      cluster_id: number;
    }[];
    file_tag: string;
    online: boolean;
  };
}

/**
 * MySQL 主从清档
 */
export interface MySQLHATruncateDetails extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    db_patterns: [];
    ignore_dbs: [];
    ignore_tables: [];
    table_patterns: [];
    force: boolean;
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
  config_id: number;
  config_data: {
    cluster_id: number;
    execute_objects: {
      data_tblist: string[];
      schema_tblist: string[];
      source_db: string;
      target_db: string;
    }[];
  }[];
  force: boolean;
  rules_set: {
    account_rules: {
      bk_biz_id: number;
      dbname: string;
    }[];
    cluster_type: string;
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
    display_info: Record<string, unknown>;
    cluster_ids: number[];
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
  BUILD_INTO_NEW_CLUSTER = 'BUILD_INTO_NEW_CLUSTER',
  BUILD_INTO_EXIST_CLUSTER = 'BUILD_INTO_EXIST_CLUSTER',
  BUILD_INTO_METACLUSTER = 'BUILD_INTO_METACLUSTER',
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
    cluster_id: number;
    databases: string[];
    databases_ignore: string[];
    tables: string[];
    tables_ignore: string[];
    rollback_host: RollbackHost;
    target_cluster_id: number;
    rollback_type: string;
    rollback_time: string;
    backupinfo: {
      backup_id: string;
      mysql_host: string;
      mysql_port: number;
      mysql_role: string;
      backup_time: string;
      backup_type: string;
      master_host: string;
      master_port: number;
    };
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
    cluster_ids: number[];
    cluster_id: number;
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
    ignore_dbs: string[];
    ignore_tables: string[];
    table_patterns: string[];
    force: boolean;
  }[];
}

/**
 * MySQL 数据导出
 */
export interface MySQLExportData extends DetailBase {
  clusters: DetailClusters;
  cluster_id: number;
  charset: string;
  databases: string[];
  tables: string[];
  tables_ignore: string[];
  where: string;
  dump_data: boolean; // 是否导出表数据
  dump_schema: boolean; // 是否导出表结构
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
  infos: {
    pkg_id: string;
    cluster_ids: number[];
    display_info: {
      current_version: string;
    };
  }[];
  force: boolean;
}

/**
 * MySQL 原地升级
 */
export interface MySQLLocalUpgradeDetails extends DetailBase {
  clusters: DetailClusters;
  infos: {
    pkg_id: number;
    cluster_ids: number[];
    display_info: {
      cluster_type: string;
      current_version: string;
      current_package: string;
      target_package: string;
      charset: string;
      current_module_name: string;
    };
  }[];
  force: boolean;
}

/**
 * MySQL 迁移升级
 */
export interface MySQLMigrateUpgradeDetails extends DetailBase {
  clusters: DetailClusters;
  ip_source: string;
  backup_source: string;
  infos: {
    cluster_ids: number[];
    new_db_module_id: number;
    pkg_id: string;
    new_master: MysqlIpItem;
    new_slave: MysqlIpItem;
    read_only_slaves?: {
      old_slave: MysqlIpItem;
      new_slave: MysqlIpItem;
    }[];
    display_info: {
      current_version: string;
      target_version: string;
      current_package: string;
      target_package: string;
      charset: string;
      current_module_name: string;
      target_module_name: string;
      old_master_slave?: string[];
    };
  }[];
  force: boolean;
}

/**
 * MySQL 权限规则变更
 */
export interface MySQLAccountRuleChangeDetails extends DetailBase {
  last_account_rules: AccountRule & {
    userName: string;
  };
  action: 'change' | 'delete';
  account_id: number;
  access_db: string;
  privilege: AccountRulePrivilege;
  bk_biz_id: number;
  account_type: string;
  rule_id: number;
}
