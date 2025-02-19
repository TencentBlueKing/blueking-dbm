import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 主从集群禁用
 */
export interface HaDisable extends DetailBase {
  cluster_ids: number[];
  clusters: DetailClusters;
  force: boolean;
}
