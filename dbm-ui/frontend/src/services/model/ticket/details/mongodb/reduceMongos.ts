import type { DetailBase, DetailClusters } from '../common';

export interface ReduceMongos extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    reduce_count: number;
    reduce_nodes: {
      ip: string;
      bk_host_id: number;
      bk_cloud_id: number;
    }[];
    role: string;
  }[];
  is_safe: boolean;
}
