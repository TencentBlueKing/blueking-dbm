import type { DetailBase, DetailClusters } from '../common';

export interface ProxyClose extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
}
