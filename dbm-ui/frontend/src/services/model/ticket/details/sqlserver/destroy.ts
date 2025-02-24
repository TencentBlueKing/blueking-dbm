import type { DetailBase, DetailClusters } from '../common';

export interface Destroy extends DetailBase {
  cluster_ids: number[];
  clusters: DetailClusters;
  force: boolean;
}
