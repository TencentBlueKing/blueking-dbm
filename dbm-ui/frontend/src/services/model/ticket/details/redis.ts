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
import {
  CopyModes,
  DisconnectModes,
  RemindFrequencyModes,
  RepairAndVerifyFrequencyModes,
  RepairAndVerifyModes,
  WriteModes,
} from '@services/model/redis/redis-dst-history-job';
import type { ExecuteModes, HostInfo, OnlineSwitchType, RepairModes } from '@services/types';

import type { ClusterTypes } from '@common/const';

import type { DetailBase, DetailClusters, DetailSpecs, SpecInfo } from './common';

// redis 新建从库
export interface RedisAddSlaveDetails extends DetailBase {
  clusters: DetailClusters;
  infos: {
    bk_cloud_id: number;
    cluster_id?: number; // 旧协议，兼容旧单据用
    cluster_ids: number[];
    pairs: {
      redis_master: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      };
      redis_slave: {
        count: number;
        old_slave_ip: string;
        spec_id: number;
      };
    }[];
  }[];
  ip_source: 'resource_pool';
  specs: DetailSpecs;
}

// redis CLB
export interface RedisCLBDetails extends DetailBase {
  cluster_id: number;
  clusters: {
    [key: string]: {
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
      tag: string[];
      time_zone: string;
      updater: string;
    };
  };
}

// redis 集群容量变更
export interface RedisScaleUpDownDetails extends DetailBase {
  clusters: DetailClusters;
  infos: {
    bk_cloud_id: number;
    capacity: number;
    cluster_id: number;
    db_version: string;
    future_capacity: number;
    group_num: number;
    online_switch_type: OnlineSwitchType;
    resource_spec: {
      backend_group: {
        affinity: 'CROS_SUBZONE';
        count: number; // 机器组数
        spec_id: number;
      };
    };
    shard_num: number;
    update_mode: string;
  }[];
  ip_source: 'resource_pool';
  specs: DetailSpecs;
}

// redis 集群分片变更
export interface RedisClusterShardUpdateDetails extends DetailBase {
  clusters: DetailClusters;
  data_check_repair_setting: {
    execution_frequency: RepairAndVerifyFrequencyModes;
    type: RepairAndVerifyModes;
  };
  infos: {
    capacity: number;
    cluster_shard_num: number;
    current_shard_num: number;
    current_spec_id: string;
    db_version: string;
    future_capacity: number;
    online_switch_type: 'user_confirm';
    resource_spec: {
      backend_group: {
        affinity: 'CROS_SUBZONE';
        count: number; // 机器组数
        spec_id: number;
      };
      proxy: {
        affinity: 'CROS_SUBZONE';
        count: number;
        spec_id: number;
      };
    };
    src_cluster: number;
  }[];
  ip_source: 'resource_pool';
  specs: DetailSpecs;
}

// redis 集群类型变更
export interface RedisClusterTypeUpdateDetails extends DetailBase {
  clusters: DetailClusters;
  data_check_repair_setting: {
    execution_frequency: RepairAndVerifyFrequencyModes;
    type: RepairAndVerifyModes;
  };
  infos: {
    capacity: number;
    cluster_shard_num: number;
    current_cluster_type: string;
    current_shard_num: number;
    current_spec_id: string;
    db_version: string;
    future_capacity: number;
    online_switch_type: 'user_confirm';
    resource_spec: {
      backend_group: {
        affinity: 'CROS_SUBZONE';
        count: number; // 机器组数
        spec_id: number;
      };
      proxy: {
        affinity: 'CROS_SUBZONE';
        count: number;
        spec_id: number;
      };
    };
    src_cluster: number;
    target_cluster_type: string;
  }[];
  ip_source: 'resource_pool';
  specs: DetailSpecs;
}

// redis 数据校验与修复
export interface RedisDataCheckAndRepairDetails extends DetailBase {
  check_stop_time: string; // 校验终止时间,
  clusters: DetailClusters;
  data_repair_enabled: boolean; // 是否修复数据
  execute_mode: ExecuteModes;
  infos: [
    {
      bill_id: number; // 关联的(数据复制)单据ID
      dst_cluster: string; // 目的集群,来自于数据复制记录
      key_black_regex: string; // 排除key
      key_white_regex: string; // 包含key
      src_cluster: string; // 源集群,来自于数据复制记录
      src_instances: string[]; // 源实例列表
    },
  ];
  keep_check_and_repair: boolean; // 是否一直保持校验
  repair_mode: RepairModes;
  specified_execution_time: string; // 定时执行,指定执行时间
}

export enum RedisClusterType {
  REDIS_CLUSTER = 'RedisCluster', // 集群版
  REDIS_INSTANCE = 'RedisInstance', // 主从版
}

// redis 数据复制
export interface RedisDataCopyDetails extends DetailBase {
  clusters: DetailClusters;
  data_check_repair_setting: {
    execution_frequency: RepairAndVerifyFrequencyModes;
    type: RepairAndVerifyModes;
  };
  dts_copy_type: CopyModes;
  infos: {
    dst_bk_biz_id: number;
    dst_cluster: number;
    key_black_regex: string; // 排除key
    key_white_regex: string; // 包含key
    src_cluster: number;
    src_cluster_password: string;
    src_cluster_type: RedisClusterType;
  }[];
  sync_disconnect_setting: {
    reminder_frequency: RemindFrequencyModes;
    type: DisconnectModes;
  };
  write_mode: WriteModes;
}

// redis 定点构造
export interface RedisDataStructrueDetails extends DetailBase {
  clusters: DetailClusters;
  infos: {
    bk_cloud_id: number;
    cluster_id: number;
    master_instances: string[];
    recovery_time_point: string;
    resource_spec: {
      redis: {
        count: number;
        spec_id: number;
      };
    };
  }[];
  ip_source: 'resource_pool';
  specs: DetailSpecs;
}

// redis 整机替换
export interface RedisDBReplaceDetails extends DetailBase {
  clusters: DetailClusters;
  infos: {
    bk_cloud_id: number;
    cluster_id?: number; // 旧协议，兼容旧单据用
    cluster_ids: number[];
    display_info: {
      data: {
        cluster_domain: string;
        ip: string;
        role: string;
        spec_id: number;
        spec_name: string;
      }[];
    };
    proxy: {
      ip: string;
      spec_id: number;
    }[];
    redis_master: {
      ip: string;
      spec_id: number;
    }[];
    redis_slave: {
      ip: string;
      spec_id: number;
    }[];
  }[];
  ip_source: 'resource_pool';
  specs: DetailSpecs;
}

export interface RedisDetails extends DetailBase {
  bk_cloud_id: number;
  cap_key: string;
  cap_spec: string;
  city_code: string;
  city_name: string;
  cluster_alias: string;
  cluster_name: string;
  cluster_type: ClusterTypes;
  db_app_abbr: string;
  db_version: string;
  disaster_tolerance_level: string;
  ip_source: string;
  nodes: {
    master: HostInfo[];
    proxy: HostInfo[];
    slave: HostInfo[];
  };
  proxy_port: number;
  proxy_pwd: string;
  resource_spec: {
    backend_group: {
      affinity: string;
      count: number;
      location_spec: {
        city: string;
        sub_zone_ids: number[];
      };
      spec_id: number;
      spec_info: {
        cluster_capacity: number;
        cluster_shard_num: number;
        machine_pair: number;
        qps?: {
          max: number;
          min: number;
        };
        spec_name: string;
      };
    };
    proxy: SpecInfo;
  };
}

// redis 主从切换
export interface RedisMasterSlaveSwitchDetails extends DetailBase {
  clusters: DetailClusters;
  force: boolean;
  infos: {
    cluster_id?: number; // 旧协议，兼容旧单据用
    cluster_ids: number[];
    online_switch_type: 'user_confirm' | 'no_confirm';
    pairs: {
      redis_master: string;
      redis_slave: string;
    }[];
  }[];
}

// redis-提取key | 删除key 详情
export interface RedisKeysDetails extends DetailBase {
  clusters: DetailClusters;
  delete_type: string;
  rules: {
    backup_type: string;
    black_regex: string;
    cluster_id: number;
    create_at: string;
    domain: string;
    path: string;
    target: string;
    total_size: string;
    white_regex: string;
  }[];
}

// redis 接入层缩容
export interface RedisProxyScaleDownDetails extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    online_switch_type: 'user_confirm' | 'no_confirm';
    proxy_reduce_count?: number;
    proxy_reduced_hosts?: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
    target_proxy_count?: number;
  }[];
  ip_source: 'resource_pool';
}

// redis 接入层扩容
export interface RedisProxyScaleUpDetails extends DetailBase {
  clusters: DetailClusters;
  infos: {
    bk_cloud_id: number;
    cluster_id: number;
    resource_spec: {
      proxy: {
        count: number;
        spec_id: number;
      };
    };
    target_proxy_count: number;
  }[];
  ip_source: 'resource_pool';
  specs: DetailSpecs;
}

// redis 以构造实例恢复
export interface RedisRollbackDataCopyDetails extends DetailBase {
  clusters: DetailClusters;
  //  dts 复制类型: 回档临时实例数据回写
  dts_copy_type: 'copy_from_rollback_instance';
  infos: {
    dst_cluster: number;
    key_black_regex: string; // 排除key
    key_white_regex: string; // 包含key
    recovery_time_point: string; // 构造到指定时间
    src_cluster: string; // 构造产物访问入口
  }[];
  write_mode: WriteModes;
}

// redis 构造销毁
export interface RedisStructureDeleteDetails extends DetailBase {
  infos: {
    bk_cloud_id: number;
    display_info: {
      temp_cluster_proxy: string;
    };
    prod_cluster: string;
    related_rollback_bill_id: number;
  }[];
}

// redis 版本升级
export interface RedisVersionUpgrade extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_ids: number[];
    current_versions: string[];
    node_type: string;
    target_version: string;
  }[];
}

// redis 安装Module
export interface RedisInstallModuleDetails extends DetailBase {
  bk_cloud_id: number;
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    db_version: string;
    load_modules: string[];
  }[];
}

// redis 迁移
export interface RedisMigrate extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    old_nodes: {
      master: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
      }[];
      slave: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
      }[];
    };
    resource_spec: {
      backend_group: {
        count: number;
        spec_id: number;
      };
    };
  }[];
}

// redis 集群迁移
export interface RedisClusterMigrate extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    display_info: {
      db_version: string[];
      instance: string;
    };
    old_nodes: {
      master: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
      }[];
      slave: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
      }[];
    };
    resource_spec: {
      backend_group: {
        count: number;
        spec_id: number;
      };
    };
  }[];
  specs: DetailSpecs;
}

// redis 主从迁移
export interface RedisSingleMigrate extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    db_version: string;
    display_info: {
      domain: string;
      ip: string;
      migrate_type: string; // domain | machine
    };
    old_nodes: {
      master: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
      }[];
      slave: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
      }[];
    };
    resource_spec: {
      backend_group: {
        count: number;
        spec_id: number;
      };
    };
  }[];
  specs: DetailSpecs;
}
