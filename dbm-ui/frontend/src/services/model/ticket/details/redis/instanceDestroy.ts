import type { DetailBase, DetailClusters } from '../common';

export interface InstanceDestroy extends DetailBase {
  cluster_ids: number[];
  clusters: DetailClusters;
}
