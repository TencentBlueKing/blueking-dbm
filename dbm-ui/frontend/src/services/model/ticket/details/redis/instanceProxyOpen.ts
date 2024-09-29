import type { DetailBase, DetailClusters } from '../common';

export interface InstanceProxyOpen extends DetailBase {
  clusters: DetailClusters;
  cluster_ids: number[];
}
