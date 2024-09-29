import type { DetailBase, DetailClusters } from '../common';

export interface ProxyClose extends DetailBase {
  clusters: DetailClusters;
  cluster_id: number;
}
