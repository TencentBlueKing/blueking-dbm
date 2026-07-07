import type { DetailBase, DetailClusters } from '../common';

/**
 * Qdrant 集群重启
 */
export interface Restart extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
}
