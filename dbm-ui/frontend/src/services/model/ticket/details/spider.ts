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

// spider 部署
export interface SpiderApplyDetails {
  bk_cloud_id: number;
  db_app_abbr: string;
  cluster_name: string;
  cluster_alias: string;
  ip_source: string;
  city_code: string;
  db_module_id: number;
  spider_port: number;
  cluster_shard_num: number;
  remote_shard_num: number;
  bk_cloud_name: string;
  charset: string;
  version: {
    db_version: string;
    spider_version: string;
  };
  db_module_name: string;
  city_name: string;
  machine_pair_cnt: number;
  disaster_tolerance_level: string;
  resource_spec: {
    spider: SpecInfo;
    backend_group: {
      count: number;
      spec_id: number;
      spec_info: ClusterSpecModel;
      capacity: string;
      future_capacity: string;
    };
  };
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
  clusters: DetailClusters;
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
  clusters: DetailClusters;
  specs: DetailSpecs;
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
  clusters: DetailClusters;
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
  force: boolean;
  infos: {
    cluster_id: number;
    from_database: string;
    to_database: string;
  }[];
  clusters: DetailClusters;
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
        bk_host_id: number;
      };
      slave: {
        ip: string;
        bk_cloud_id: number;
        bk_host_id: number;
      };
    }[];
  }[];
  clusters: DetailClusters;
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
  clusters: DetailClusters;
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
  clusters: DetailClusters;
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
  clusters: DetailClusters;
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
  clusters: DetailClusters;
}

// Spider 集群remote节点扩缩容
export interface SpiderNodeRebalanceDetails {
  backup_source: string;
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
        futureCapacity: number;
        specName: string;
      };
    };
  }[];
  clusters: DetailClusters;
}

// spider 定点回档
export interface SpiderRollbackDetails {
  cluster_id: number;
  clusters: DetailClusters;
  rollback_type: 'REMOTE_AND_BACKUPID' | 'REMOTE_AND_TIME';
  rollback_time: string;
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
  databases: string[];
  tables: string[];
  databases_ignore: string[];
  tables_ignore: string[];
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
  clusters: DetailClusters;
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
  clusters: DetailClusters;
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

// spider 迁移主从
export interface SpiderSlaveRebuid {
  infos: {
    cluster_id: number;
    slave: {
      ip: string;
      bk_biz_id: number;
      bk_host_id: number;
      bk_cloud_id: number;
      port: number;
    };
    old_slave: SpiderSlaveRebuid['infos'][number]['slave'];
    new_slave: SpiderSlaveRebuid['infos'][number]['slave'];
    resource_spec: {
      new_slave: {
        name: string;
        cpu: {
          max: number;
          min: number;
        };
        id: number;
        mem: {
          max: number;
          min: number;
        };
        qps: {
          max: number;
          min: number;
        };
        count: number;
        storage_spec: {
          mount_point: string;
          size: number;
          type: string;
        }[];
      };
    };
  }[];
  clusters: DetailClusters;
  ip_source: string;
  backup_source: string;
}

// spider 迁移主从
export interface SpiderMigrateCluster {
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
  clusters: DetailClusters;
  ip_source: string;
  backup_source: string;
}
