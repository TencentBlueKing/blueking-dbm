import type { DetailBase, DetailClusters } from '../common';

/**
 * SurrealDB 集群销毁
 */
export interface DELETE extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
}
