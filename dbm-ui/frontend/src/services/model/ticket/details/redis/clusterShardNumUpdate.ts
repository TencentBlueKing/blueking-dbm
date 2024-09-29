import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface ClusterShardNumUpdate extends DetailBase {
  clusters: DetailClusters;
  data_check_repair_setting: {
    type: string;
    execution_frequency: string;
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
