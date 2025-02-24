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

import ClusterSpecModel from '@services/model/resource-spec/cluster-sepc';

import type { DetailClusters, DetailSpecs, SpecInfo } from './common';
import type { RollbackClusterTypes } from './mysql';

// spider 部署
export interface SpiderApplyDetails {
  bk_cloud_id: number;
  bk_cloud_name: string;
  charset: string;
  city_code: string;
  city_name: string;
  cluster_alias: string;
  cluster_name: string;
  cluster_shard_num: number;
  db_app_abbr: string;
  db_module_id: number;
  db_module_name: string;
  disaster_tolerance_level: string;
  ip_source: string;
  machine_pair_cnt: number;
  remote_shard_num: number;
  resource_spec: {
    backend_group: {
      capacity: string;
      count: number;
      future_capacity: string;
      spec_id: number;
      spec_info: ClusterSpecModel;
    };
    spider: SpecInfo;
  };
  spider_port: number;
  version: {
    db_version: string;
    spider_version: string;
  };
}

// Spider Checksum
export interface SpiderCheckSumDetails {
  clusters: DetailClusters;
  data_repair: {
    is_repair: boolean;
    mode: 'timer' | 'manual';
  };
  infos: {
    backup_infos: {
      db_patterns: string[];
      ignore_dbs: string[];
      ignore_tables: string[];
      master: string;
      slave: string;
      table_patterns: string[];
    }[];
    checksum_scope: 'partial' | 'all';
    cluster_id: number;
  }[];
  is_sync_non_innodb: true;
  runtime_hour: number;
  timing: string;
}

// Spider slave集群添加
export interface SpiderSlaveApplyDetails {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    resource_spec: {
      spider_slave_ip_list: {
        count: number;
        spec_id: number;
      };
    };
  }[];
  ip_source: 'manual_input';
  specs: DetailSpecs;
}

// Spider 临时节点添加
export interface SpiderMNTApplyDetails {
  clusters: DetailClusters;
  infos: {
    bk_cloud_id: number;
    cluster_id: number;
    immutable_domain: string;
    spider_ip_list: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
  }[];
}

// Spider 集群下架
export interface SpiderDestroyDetails {
  cluster_ids: number[]; // 待下架的id 列表
  force: boolean; // 实例强制下架，默认先给false
}

// Spider 集群启动
export interface SpiderEnableDetails {
  cluster_ids: number[]; // 待下架的id 列表
  is_only_add_slave_domain: boolean; // 只启用只读集群的话, 这个参数为true
}

// Spider 集群禁用
export interface SpiderDisableDetails {
  cluster_ids: number[]; // 待禁用的id 列表
}

// Spider Tendbcluster 重命名
export interface SpiderRenameDatabaseDetails {
  clusters: DetailClusters;
  force: boolean;
  infos: {
    cluster_id: number;
    from_database: string;
    to_database: string;
  }[];
}

// Spider remote 主从互切
export interface SpiderMasterSlaveSwitchDetails {
  clusters: DetailClusters;
  force: boolean; // 互切单据就传False，表示安全切换
  infos: {
    cluster_id: 1;
    switch_tuples: {
      master: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      };
      slave: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      };
    }[];
  }[];
  is_check_delay: boolean; // 目前互切单据延时属于强制检测，故必须传True， 用户没有选择
  is_check_process: boolean;
  is_verify_checksum: boolean;
}

// Spider remote主故障切换
export type SpiderMasterFailoverDetails = SpiderMasterSlaveSwitchDetails;

// spider扩容接入层
export interface SpiderAddNodesDeatils {
  clusters: DetailClusters;
  infos: {
    add_spider_role: string;
    cluster_id: number;
    resource_spec: {
      spider_ip_list: {
        count: number;
        spec_id: number;
      };
    };
  }[];
  ip_source: 'resource_pool';
}

// Spider TenDBCluster 库表备份
export interface SpiderTableBackupDetails {
  clusters: DetailClusters;
  infos: {
    backup_local: string;
    cluster_id: number;
    db_patterns: string[];
    ignore_dbs: string[];
    ignore_tables: string[];
    table_patterns: string[];
  }[];
}

// Spider TenDBCluster 全备单据
export interface SpiderFullBackupDetails {
  // 新版协议
  backup_type: 'logical' | 'physical';
  clusters: DetailClusters;
  file_tag: 'MYSQL_FULL_BACKUP' | 'LONGDAY_DBFILE_3Y';
  infos:
    | {
        // 旧版协议
        backup_type: 'logical' | 'physical';
        clusters: {
          backup_local: string; // spider_mnt:: 127.0.0.1: 8000
          cluster_id: number;
        }[];
        file_tag: 'MYSQL_FULL_BACKUP' | 'LONGDAY_DBFILE_3Y';
      }
    | {
        backup_local: string; // spider_mnt:: 127.0.0.1: 8000
        // 新版协议
        cluster_id: number;
      }[];
}

// spider 缩容接入层
export interface SpiderReduceNodesDetails {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    reduce_spider_role: string;
    spider_reduced_hosts?: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
    spider_reduced_to_count?: number;
  }[];
  is_safe: boolean; // 是否做安全检测
}

// Spider 集群remote节点扩缩容
export interface SpiderNodeRebalanceDetails {
  backup_source: string;
  clusters: DetailClusters;
  infos: {
    bk_cloud_id: number;
    cluster_id: number;
    cluster_shard_num: number; // 集群分片数
    db_module_id: number;
    remote_shard_num: number; // 单机分片数
    resource_spec: {
      backend_group: {
        affinity: string; // 亲和性要求
        count: number;
        futureCapacity: number;
        spec_id: number;
        specName: string;
      };
    };
  }[];
  need_checksum: true;
  trigger_checksum_time: string;
  trigger_checksum_type: 'now' | 'timer';
}

// spider 定点回档
export interface SpiderRollbackDetails {
  clusters: DetailClusters;
  infos: {
    backupinfo: {
      backup_begin_time: string;
      backup_end_time: string;
      backup_id: string;
      backup_time: string;
      bill_id: string;
      bk_biz_id: number;
      bk_cloud_id: number;
      cluster_address: string;
      cluster_id: number;
    };
    cluster_id: number;
    databases: string[];
    databases_ignore: string[];
    rollback_time: string;
    rollback_type: 'REMOTE_AND_BACKUPID' | 'REMOTE_AND_TIME';
    tables: string[];
    tables_ignore: string[];
    target_cluster_id: number;
  }[];
  rollback_cluster_type: RollbackClusterTypes;
}

// Spider flashback
export interface SpiderFlashbackDetails {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    databases: string[];
    databases_ignore: string[];
    end_time: string;
    start_time: string;
    tables: string[];
    tables_ignore: string[];
  }[];
}

// Spider tendbcluster 清档
export interface SpiderTruncateDatabaseDetails {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    db_patterns: string[];
    force: boolean;
    ignore_dbs: string[];
    ignore_tables: string[];
    table_patterns: string[];
    truncate_data_type: 'truncate_table' | 'drop_table' | 'drop_database';
  }[];
}

// Spider 只读集群下架
export interface SpiderSlaveDestroyDetails {
  cluster_ids: number[];
  is_safe: boolean;
}

// Spider 运维节点下架
export interface SpiderMNTDestroyDetails {
  infos: {
    cluster_id: number;
    spider_ip_list: {
      bk_cloud_id: number;
      ip: string;
    }[];
  }[];
  is_safe: boolean;
}

export interface SpiderPartitionManageDetails {
  clusters: {
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
  };
  infos: {
    bk_cloud_id: number;
    cluster_id: number;
    config_id: string;
    immute_domain: string;
    partition_objects: {
      execute_objects: [
        {
          add_partition: [];
          config_id: number;
          dblike: string;
          drop_partition: [];
          init_partition: [
            {
              need_size: number;
              sql: string;
            },
          ];
          tblike: string;
        },
      ];
      ip: string;
      port: number;
      shard_name: string;
    }[];
  }[];
}

// spider 迁移主从
export interface SpiderSlaveRebuid {
  backup_source: string;
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    new_slave: SpiderSlaveRebuid['infos'][number]['slave'];
    old_slave: SpiderSlaveRebuid['infos'][number]['slave'];
    resource_spec: {
      new_slave: {
        count: number;
        cpu: {
          max: number;
          min: number;
        };
        id: number;
        mem: {
          max: number;
          min: number;
        };
        name: string;
        qps: {
          max: number;
          min: number;
        };
        storage_spec: {
          mount_point: string;
          size: number;
          type: string;
        }[];
      };
    };
    slave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port: number;
    };
  }[];
  ip_source: string;
}

// spider 迁移主从
export interface SpiderMigrateCluster {
  backup_source: string;
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    new_master: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
    new_slave: SpiderMigrateCluster['infos'][number]['new_master'];
    old_master: SpiderMigrateCluster['infos'][number]['new_master'];
    old_slave: SpiderMigrateCluster['infos'][number]['new_master'];
  }[];
  ip_source: string;
}
