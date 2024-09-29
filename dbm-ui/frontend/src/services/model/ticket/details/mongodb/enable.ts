import type { DetailBase, DetailClusters } from '../common';

export interface Enable extends DetailBase {
  clusters: DetailClusters;
  cluster_ids: number[];
}
