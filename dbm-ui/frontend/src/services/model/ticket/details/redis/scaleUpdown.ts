import type RedisModel from '@services/model/redis/redis';
import type { OnlineSwitchType } from '@services/types';

import { Affinity } from '@common/const';

import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface ScaleUpdown extends DetailBase {
  clusters: DetailClusters;
  infos: {
    bk_cloud_id: number;
    capacity: number;
    cluster_id: number;
    db_version: string;
    display_info: Pick<
      RedisModel,
      'cluster_stats' | 'cluster_spec' | 'cluster_shard_num' | 'cluster_capacity' | 'machine_pair_cnt'
    >;
    future_capacity: number;
    group_num: number;
    online_switch_type: OnlineSwitchType;
    resource_spec: {
      backend_group: {
        affinity: Affinity;
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
