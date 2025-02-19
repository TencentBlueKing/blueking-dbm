import type { DetailBase, DetailClusters } from '../common';

export interface Destroy extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
}
