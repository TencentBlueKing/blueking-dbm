import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 主从集群可用
 */
export interface HaEnable extends DetailBase {
  force: boolean;
  clusters: DetailClusters;
  cluster_ids: number[];
}
