import type { DetailBase, DetailClusters } from '../common';

/**
 * SurrealDB 集群启用
 */
export interface Enable extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
}
