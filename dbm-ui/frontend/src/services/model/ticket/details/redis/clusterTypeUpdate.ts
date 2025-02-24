import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface ClusterTypeUpdate extends DetailBase {
  clusters: DetailClusters;
  data_check_repair_setting: {
    execution_frequency: string;
    type: string;
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
