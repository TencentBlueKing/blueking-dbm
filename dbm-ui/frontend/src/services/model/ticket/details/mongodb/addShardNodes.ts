import type { DetailBase, DetailClusters } from '../common';

export interface AddShardNodes extends DetailBase {
  clusters: DetailClusters;
  infos: {
    add_shard_nodes_num: number;
    cluster_ids: number[];
    current_shard_nodes_num: number;
    node_replica_count: number;
    resource_spec: {
      shard_nodes: {
        count: number;
        spec_id: number;
      };
    };
  }[];
  ip_source: string;
  is_safe: boolean;
}
