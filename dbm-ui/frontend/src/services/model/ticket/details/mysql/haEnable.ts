import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 主从集群可用
 */
export interface HaEnable extends DetailBase {
  cluster_ids: number[];
  clusters: DetailClusters;
  force: boolean;
}
