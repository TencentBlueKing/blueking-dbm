import type { DetailBase, DetailClusters } from '../common';

export interface DeleteClb extends DetailBase {
  bk_cloud_id: number;
  cluster_id: number;
  clusters: DetailClusters;
}
