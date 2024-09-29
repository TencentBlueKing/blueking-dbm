import type { DetailBase, DetailClusters } from '../common';

export interface InstanceDestroy extends DetailBase {
  clusters: DetailClusters;
  cluster_ids: number[];
}
