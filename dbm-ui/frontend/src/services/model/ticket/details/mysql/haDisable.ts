import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 主从集群禁用
 */
export interface HaDisable extends DetailBase {
  force: boolean;
  clusters: DetailClusters;
  cluster_ids: number[];
}
