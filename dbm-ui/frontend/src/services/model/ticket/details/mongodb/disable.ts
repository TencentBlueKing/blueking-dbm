import type { DetailBase, DetailClusters } from '../common';

export interface Disable extends DetailBase {
  cluster_ids: number[];
  clusters: DetailClusters;
}
