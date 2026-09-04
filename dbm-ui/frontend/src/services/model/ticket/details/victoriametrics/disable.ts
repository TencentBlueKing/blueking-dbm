import type { DetailBase, DetailClusters } from '../common';

/**
 * VictoriaMetrics 集群禁用
 */
export interface Disable extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
}
