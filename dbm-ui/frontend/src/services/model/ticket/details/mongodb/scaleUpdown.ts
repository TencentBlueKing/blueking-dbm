import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface ScaleUpdown extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    resource_spec: {
      mongodb: {
        count: number;
        spec_id: number;
      };
    };
    shard_machine_group: number;
    shard_node_count: number;
    shards_num: number;
  }[];
  ip_source: string;
  specs: DetailSpecs;
}
