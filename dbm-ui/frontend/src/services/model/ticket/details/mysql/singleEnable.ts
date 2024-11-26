import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 单节点集群可用
 */
export interface SingleEnable extends DetailBase {
  force: boolean;
  clusters: DetailClusters;
  cluster_ids: number[];
}
