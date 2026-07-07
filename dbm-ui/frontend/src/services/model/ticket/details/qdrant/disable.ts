import type { DetailBase, DetailClusters } from '../common';

/**
 * Qdrant 集群禁用
 */
export interface Disable extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
}
