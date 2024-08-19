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
import type { ExecuteModes, OnlineSwitchType, RepairModes } from '@services/types/common';
import type { HostDetails } from '@services/types/ip';

import type { ClusterTypes } from '@common/const';

import type { DetailBase, DetailClusters, DetailSpecs, SpecInfo } from './common';

// redis 新建从库
export interface RedisAddSlaveDetails extends DetailBase {
  clusters: DetailClusters;
  ip_source: 'resource_pool';
  infos: {
    cluster_id?: number; // 旧协议，兼容旧单据用
    cluster_ids: number[];
    bk_cloud_id: number;
    pairs: {
      redis_master: {
        ip: string;
        bk_cloud_id: number;
        bk_host_id: number;
      };
      redis_slave: {
        spec_id: number;
        count: number;
        old_slave_ip: string;
      };
    }[];
  }[];
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
  ip_source: 'resource_pool';
  infos: {
    cluster_id: number;
    bk_cloud_id: number;
    db_version: string;
    shard_num: number;
    group_num: number;
    online_switch_type: OnlineSwitchType;
    capacity: number;
    future_capacity: number;
    update_mode: string;
    resource_spec: {
      backend_group: {
        spec_id: number;
        count: number; // 机器组数
        affinity: 'CROS_SUBZONE';
      };
    };
  }[];
  specs: DetailSpecs;
}

// redis 集群分片变更
export interface RedisClusterShardUpdateDetails extends DetailBase {
  clusters: DetailClusters;
  data_check_repair_setting: {
    type: RepairAndVerifyModes;
    execution_frequency: RepairAndVerifyFrequencyModes;
  };
  ip_source: 'resource_pool';
  infos: {
    src_cluster: number;
    current_shard_num: number;
    current_spec_id: string;
    cluster_shard_num: number;
    db_version: string;
    online_switch_type: 'user_confirm';
    capacity: number;
    future_capacity: number;
    resource_spec: {
      proxy: {
        spec_id: number;
        count: number;
        affinity: 'CROS_SUBZONE';
      };
      backend_group: {
        spec_id: number;
        count: number; // 机器组数
        affinity: 'CROS_SUBZONE';
      };
    };
  }[];
  specs: DetailSpecs;
}

// redis 集群类型变更
export interface RedisClusterTypeUpdateDetails extends DetailBase {
  clusters: DetailClusters;
  data_check_repair_setting: {
    type: RepairAndVerifyModes;
    execution_frequency: RepairAndVerifyFrequencyModes;
  };
  ip_source: 'resource_pool';
  infos: {
    current_cluster_type: string;
    target_cluster_type: string;
    src_cluster: number;
    current_shard_num: number;
    current_spec_id: string;
    cluster_shard_num: number;
    db_version: string;
    online_switch_type: 'user_confirm';
    capacity: number;
    future_capacity: number;
    resource_spec: {
      proxy: {
        spec_id: number;
        count: number;
        affinity: 'CROS_SUBZONE';
      };
      backend_group: {
        spec_id: number;
        count: number; // 机器组数
        affinity: 'CROS_SUBZONE';
      };
    };
  }[];
  specs: DetailSpecs;
}

// redis 数据校验与修复
export interface RedisDataCheckAndRepairDetails extends DetailBase {
  clusters: DetailClusters;
  execute_mode: ExecuteModes;
  specified_execution_time: string; // 定时执行,指定执行时间
  check_stop_time: string; // 校验终止时间,
  keep_check_and_repair: boolean; // 是否一直保持校验
  data_repair_enabled: boolean; // 是否修复数据
  repair_mode: RepairModes;
  infos: [
    {
      bill_id: number; // 关联的(数据复制)单据ID
      src_cluster: string; // 源集群,来自于数据复制记录
      src_instances: string[]; // 源实例列表
      dst_cluster: string; // 目的集群,来自于数据复制记录
      key_white_regex: string; // 包含key
      key_black_regex: string; // 排除key
    },
  ];
}

export enum RedisClusterType {
  REDIS_INSTANCE = 'RedisInstance', // 主从版
  REDIS_CLUSTER = 'RedisCluster', // 集群版
}

// redis 数据复制
export interface RedisDataCopyDetails extends DetailBase {
  clusters: DetailClusters;
  dts_copy_type: CopyModes;
  write_mode: WriteModes;
  sync_disconnect_setting: {
    type: DisconnectModes;
    reminder_frequency: RemindFrequencyModes;
  };
  data_check_repair_setting: {
    type: RepairAndVerifyModes;
    execution_frequency: RepairAndVerifyFrequencyModes;
  };
  infos: {
    src_cluster: number;
    dst_cluster: number;
    key_white_regex: string; // 包含key
    key_black_regex: string; // 排除key
    src_cluster_type: RedisClusterType;
    src_cluster_password: string;
    dst_bk_biz_id: number;
  }[];
}

// redis 定点构造
export interface RedisDataStructrueDetails extends DetailBase {
  clusters: DetailClusters;
  ip_source: 'resource_pool';
  infos: {
    cluster_id: number;
    bk_cloud_id: number;
    master_instances: string[];
    recovery_time_point: string;
    resource_spec: {
      redis: {
        spec_id: number;
        count: number;
      };
    };
  }[];
  specs: DetailSpecs;
}

// redis 整机替换
export interface RedisDBReplaceDetails extends DetailBase {
  clusters: DetailClusters;
  ip_source: 'resource_pool';
  infos: {
    cluster_id?: number; // 旧协议，兼容旧单据用
    cluster_ids: number[];
    bk_cloud_id: number;
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
  specs: DetailSpecs;
}

export interface RedisDetails extends DetailBase {
  bk_cloud_id: number;
  cap_key: string;
  city_code: string;
  city_name: string;
  cluster_alias: string;
  cluster_name: string;
  cluster_type: ClusterTypes;
  cap_spec: string;
  db_version: string;
  db_app_abbr: string;
  disaster_tolerance_level: string;
  ip_source: string;
  nodes: {
    proxy: HostDetails[];
    master: HostDetails[];
    slave: HostDetails[];
  };
  proxy_port: number;
  proxy_pwd: string;
  resource_spec: {
    proxy: SpecInfo;
    backend_group: {
      affinity: string;
      count: number;
      spec_id: number;
      spec_info: SpecInfo;
      location_spec: {
        city: string;
        sub_zone_ids: number[];
      };
    };
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
  delete_type: string;
  rules: {
    black_regex: string;
    cluster_id: number;
    domain: string;
    path: string;
    total_size: string;
    white_regex: string;
    create_at: string;
    target: string;
    backup_type: string;
  }[];
  clusters: DetailClusters;
}

// redis 接入层缩容
export interface RedisProxyScaleDownDetails extends DetailBase {
  clusters: DetailClusters;
  ip_source: 'resource_pool';
  infos: {
    cluster_id: number;
    target_proxy_count?: number;
    proxy_reduced_hosts?: {
      ip: string;
      bk_host_id: number;
      bk_cloud_id: number;
      bk_biz_id: number;
    }[];
    online_switch_type: 'user_confirm' | 'no_confirm';
  }[];
}

// redis 接入层扩容
export interface RedisProxyScaleUpDetails extends DetailBase {
  clusters: DetailClusters;
  ip_source: 'resource_pool';
  infos: {
    cluster_id: number;
    bk_cloud_id: number;
    target_proxy_count: number;
    resource_spec: {
      proxy: {
        spec_id: number;
        count: number;
      };
    };
  }[];
  specs: DetailSpecs;
}

// redis 以构造实例恢复
export interface RedisRollbackDataCopyDetails extends DetailBase {
  clusters: DetailClusters;
  //  dts 复制类型: 回档临时实例数据回写
  dts_copy_type: 'copy_from_rollback_instance';
  write_mode: WriteModes;
  infos: {
    src_cluster: string; // 构造产物访问入口
    dst_cluster: number;
    key_white_regex: string; // 包含key
    key_black_regex: string; // 排除key
    recovery_time_point: string; // 构造到指定时间
  }[];
}

// redis 构造销毁
export interface RedisStructureDeleteDetails extends DetailBase {
  infos: {
    related_rollback_bill_id: number;
    prod_cluster: string;
    bk_cloud_id: number;
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
