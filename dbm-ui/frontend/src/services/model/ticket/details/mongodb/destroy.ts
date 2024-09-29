import type { DetailBase, DetailClusters } from '../common';

export interface Destroy extends DetailBase {
  clusters: DetailClusters;
  cluster_ids: number[];
}
