import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 集群操作
 */
export interface ClusterSwitch extends DetailBase {
  force: boolean;
  clusters: DetailClusters;
  cluster_ids: number[];
}
