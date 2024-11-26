import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 单节点集群禁用
 */
export interface SingleDisable extends DetailBase {
  force: boolean;
  clusters: DetailClusters;
  cluster_ids: number[];
}
