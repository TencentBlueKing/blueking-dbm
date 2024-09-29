import type { DetailBase, DetailClusters } from '../common';

export interface ProxyOpen extends DetailBase {
  clusters: DetailClusters;
  cluster_id: number;
}
