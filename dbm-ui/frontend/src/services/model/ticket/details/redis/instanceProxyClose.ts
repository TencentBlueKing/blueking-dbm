import type { DetailBase, DetailClusters } from '../common';

export interface InstanceProxyClose extends DetailBase {
  cluster_ids: number[];
  clusters: DetailClusters;
}
