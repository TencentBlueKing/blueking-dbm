import type { DetailBase, DetailClusters } from '../common';

export interface Disable extends DetailBase {
  clusters: DetailClusters;
  cluster_ids: number[];
}
