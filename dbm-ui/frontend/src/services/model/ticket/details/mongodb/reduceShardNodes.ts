import type { DetailBase, DetailClusters } from '../common';

export interface ReduceShardNodes extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_ids: number[];
    current_shard_nodes_num: number;
    reduce_shard_nodes: number;
    shard_num: number;
    machine_instance_num: number;
  }[];
  is_safe: boolean;
  // ip_source: string;
}
