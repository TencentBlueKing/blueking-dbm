import type { DetailBase, DetailClusters } from '../common';

/**
 * VictoriaMetrics 集群重启
 */
export interface Restart extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
}
