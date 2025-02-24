import type { DetailBase, DetailClusters } from '../common';

export interface ProxyOpen extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
}
