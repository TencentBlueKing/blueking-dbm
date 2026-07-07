import type { DetailBase, DetailClusters } from '../common';

/**
 * Qdrant 集群销毁
 */
export interface Delete extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
}
