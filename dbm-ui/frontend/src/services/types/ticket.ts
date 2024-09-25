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
import type { HostInfo } from '@services/types';

import { TicketTypes } from '@common/const';

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
  cost_time: number;
  context: {
    expire_time?: number;
  };
  err_code: number;
  err_msg: string;
  end_time: string;
  flow_type: string;
  flow_type_display: string;
  flow_obj_id: string;
  flow_expire_time?: number;
  id: number;
  status: 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'SKIPPED' | 'REVOKED' | 'TERMINATED';
  start_time: string;
  summary: string;
  ticket: number;
  todos: FlowItemTodo[];
  update_at: string;
  url: string;
  details: {
    ticket_data: MySQLImportSQLFileDetails;
    operators?: string[]; // 系统单据处理人才会有这个
  };
}

/**
 * 单据流程待办信息
 */
export interface FlowItemTodo {
  context: {
    flow_id: number;
    ticket_id: number;
    node_id: string;
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
    client: HostInfo[];
    master: HostInfo[];
    hot: HostInfo[];
    cold: HostInfo[];
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
    datanode: HostInfo[];
    namenode: HostInfo[];
    zookeeper: HostInfo[];
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
    broker: HostInfo[];
    zookeeper: HostInfo[];
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
  datanode: HostInfo[];
  hot: HostInfo[];
  cold: HostInfo[];
  master: HostInfo[];
  client: HostInfo[];
  namenode: HostInfo[];
  zookeeper: HostInfo[];
  broker: HostInfo[];
  proxy: HostInfo[];
  slave: HostInfo[];
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

export interface MysqlIpItem {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_host_id: number;
  ip: string;
  port?: number;
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

// Spider Checksum
export interface SpiderCheckSumDetails {
  data_repair: {
    is_repair: boolean;
    mode: 'timer' | 'manual';
  };
  is_sync_non_innodb: true;
  timing: string;
  runtime_hour: number;
  infos: {
    cluster_id: number;
    checksum_scope: 'partial' | 'all';
    backup_infos: {
      master: string;
      slave: string;
      db_patterns: string[];
      ignore_dbs: string[];
      table_patterns: string[];
      ignore_tables: string[];
    }[];
  }[];
}

// Spider slave集群添加
export interface SpiderSlaveApplyDetails {
  ip_source: 'manual_input';
  infos: {
    cluster_id: number;
    resource_spec: {
      spider_slave_ip_list: {
        spec_id: number;
        count: number;
      };
    };
  }[];
}

// Spider 临时节点添加
export interface SpiderMNTApplyDetails {
  infos: {
    cluster_id: number;
    bk_cloud_id: number;
    spider_ip_list: {
      ip: string;
      bk_cloud_id: number;
      bk_host_id: number;
    }[];
    immutable_domain: string;
  }[];
}

// Spider 集群下架
export interface SpiderDestroyDetails {
  force: boolean; // 实例强制下架，默认先给false
  cluster_ids: number[]; // 待下架的id 列表
}

// Spider 集群启动
export interface SpiderEnableDetails {
  is_only_add_slave_domain: boolean; // 只启用只读集群的话, 这个参数为true
  cluster_ids: number[]; // 待下架的id 列表
}

// Spider 集群禁用
export interface SpiderDisableDetails {
  cluster_ids: number[]; // 待禁用的id 列表
}

// Spider Tendbcluster 重命名
export interface SpiderRenameDatabaseDetails {
  infos: {
    cluster_id: number;
    from_database: string;
    to_database: string;
    force: boolean;
  }[];
}

// Spider remote 主从互切
export interface SpiderMasterSlaveSwitchDetails {
  force: boolean; // 互切单据就传False，表示安全切换
  is_check_process: boolean;
  is_verify_checksum: boolean;
  is_check_delay: boolean; // 目前互切单据延时属于强制检测，故必须传True， 用户没有选择
  infos: {
    cluster_id: 1;
    switch_tuples: {
      master: {
        ip: string;
        bk_cloud_id: number;
      };
      slave: {
        ip: string;
        bk_cloud_id: number;
      };
    }[];
  }[];
}

// Spider remote主故障切换
export type SpiderMasterFailoverDetails = SpiderMasterSlaveSwitchDetails;

// spider扩容接入层
export interface SpiderAddNodesDeatils {
  ip_source: 'resource_pool';
  infos: {
    cluster_id: number;
    add_spider_role: string;
    resource_spec: {
      spider_ip_list: {
        count: number;
        spec_id: number;
      };
    };
  }[];
}

// Spider TenDBCluster 库表备份
export interface SpiderTableBackupDetails {
  infos: {
    cluster_id: number;
    db_patterns: string[];
    ignore_dbs: string[];
    table_patterns: string[];
    ignore_tables: string[];
    backup_local: string;
  }[];
}

// Spider TenDBCluster 全备单据
export interface SpiderFullBackupDetails {
  infos: {
    backup_type: 'logical' | 'physical';
    file_tag: 'MYSQL_FULL_BACKUP' | 'LONGDAY_DBFILE_3Y';
    clusters: {
      cluster_id: number;
      backup_local: string; // spider_mnt:: 127.0.0.1: 8000
    }[];
  };
}

// spider 缩容接入层
export interface SpiderReduceNodesDetails {
  is_safe: boolean; // 是否做安全检测
  infos: {
    cluster_id: number;
    reduce_spider_role: string;
    spider_reduced_to_count?: number;
    spider_reduced_hosts?: {
      ip: string;
      bk_host_id: number;
      bk_cloud_id: number;
      bk_biz_id: number;
    }[];
  }[];
}

// Spider 集群remote节点扩缩容
export interface SpiderNodeRebalanceDetails {
  need_checksum: true;
  trigger_checksum_type: 'now' | 'timer';
  trigger_checksum_time: string;
  infos: {
    bk_cloud_id: number;
    cluster_id: number;
    db_module_id: number;
    cluster_shard_num: number; // 集群分片数
    remote_shard_num: number; // 单机分片数
    resource_spec: {
      backend_group: {
        spec_id: number;
        count: number;
        affinity: string; // 亲和性要求
      };
    };
    prev_machine_pair: number;
    prev_cluster_spec_name: string;
  }[];
}

// Spider flashback
export interface SpiderFlashbackDetails {
  infos: {
    cluster_id: number;
    start_time: string;
    end_time: string;
    databases: string[];
    databases_ignore: string[];
    tables: string[];
    tables_ignore: string[];
  }[];
}

// Spider tendbcluster 清档
export interface SpiderTruncateDatabaseDetails {
  infos: {
    cluster_id: number;
    db_patterns: string[];
    ignore_dbs: string[];
    table_patterns: string[];
    ignore_tables: string[];
    truncate_data_type: 'truncate_table' | 'drop_table' | 'drop_database';
    force: boolean;
  }[];
}

// Spider 只读集群下架
export interface SpiderSlaveDestroyDetails {
  is_safe: boolean;
  cluster_ids: number[];
}

// Spider 运维节点下架
export interface SpiderMNTDestroyDetails {
  is_safe: boolean;
  infos: {
    cluster_id: number;
    spider_ip_list: {
      ip: string;
      bk_cloud_id: number;
    }[];
  }[];
}

export interface SpiderPartitionManageDetails {
  infos: {
    config_id: string;
    cluster_id: number;
    bk_cloud_id: number;
    immute_domain: string;
    partition_objects: {
      ip: string;
      port: number;
      shard_name: string;
      execute_objects: [
        {
          dblike: string;
          tblike: string;
          config_id: number;
          add_partition: [];
          drop_partition: [];
          init_partition: [
            {
              sql: string;
              need_size: number;
            },
          ];
        },
      ];
    }[];
  }[];
  clusters: {
    [key: number]: {
      id: number;
      name: string;
      alias: string;
      phase: string;
      region: string;
      status: string;
      creator: string;
      updater: string;
      bk_biz_id: number;
      time_zone: string;
      bk_cloud_id: number;
      cluster_type: string;
      db_module_id: number;
      immute_domain: string;
      major_version: string;
      cluster_type_name: string;
    };
  };
}

export interface MysqlDataMigrateDetails {
  clusters: clustersItems;
  infos: {
    db_list: string;
    source_cluster: number;
    target_clusters: number[];
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
