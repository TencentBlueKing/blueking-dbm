import RedisModel from '@services/model/redis/redis';

import { Affinity } from '@common/const';

import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface ClusterShardNumUpdate extends DetailBase {
  clusters: DetailClusters;
  data_check_repair_setting: {
    execution_frequency: string;
    type: string;
  };
  infos: {
    capacity: number;
    cluster_shard_num: number;
    cluster_spec?: RedisModel['cluster_spec']; // 展示字段，需兼容旧单据，下同
    cluster_stats?: RedisModel['cluster_stats']; // 展示字段
    current_shard_num: number;
    current_spec_id: string;
    db_version: string;
    future_capacity: number;
    machine_pair_cnt?: number; // 展示字段
    online_switch_type: 'user_confirm';
    proxy?: RedisModel['proxy']; // 展示字段
    resource_spec: {
      backend_group: {
        affinity: Affinity.CROS_SUBZONE;
        count: number; // 机器组数
        spec_id: number;
      };
      proxy: {
        affinity: Affinity.CROS_SUBZONE;
        count: number;
        spec_id: number;
      };
    };
    src_cluster: number;
  }[];
  ip_source: 'resource_pool';
  specs: DetailSpecs;
}
