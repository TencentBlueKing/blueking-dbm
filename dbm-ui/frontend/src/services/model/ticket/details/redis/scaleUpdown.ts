import type RedisModel from '@services/model/redis/redis';
import type { OnlineSwitchType } from '@services/types';

import type { AffinityType } from '@views/db-manage/redis/common/types';

import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface ScaleUpdown extends DetailBase {
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
        affinity: AffinityType;
      };
    };
    display_info: Pick<
      RedisModel,
      'cluster_stats' | 'cluster_spec' | 'cluster_shard_num' | 'cluster_capacity' | 'machine_pair_cnt'
    >;
  }[];
  specs: DetailSpecs;
}
