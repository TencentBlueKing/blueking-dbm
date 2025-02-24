import type { DetailBase, DetailClusters } from '../common';

export interface Enable extends DetailBase {
  cluster_ids: number[];
  clusters: DetailClusters;
  force: boolean;
}
