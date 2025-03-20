import type { DetailBase, DetailClusters } from '../common';

export interface ReduceMongos extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    reduce_count: number;
    reduce_nodes: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
    role: string;
  }[];
  is_safe: boolean;
}
