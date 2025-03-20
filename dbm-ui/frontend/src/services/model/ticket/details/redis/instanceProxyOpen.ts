import type { DetailBase, DetailClusters } from '../common';

export interface InstanceProxyOpen extends DetailBase {
  cluster_ids: number[];
  clusters: DetailClusters;
}
