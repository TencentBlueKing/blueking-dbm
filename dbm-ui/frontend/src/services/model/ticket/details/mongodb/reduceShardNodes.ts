import type { DetailBase, DetailClusters } from '../common';

export interface ReduceShardNodes extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    reduce_shard_nodes: number;
  }[];
  is_safe: boolean;
  ip_source: string;
}
