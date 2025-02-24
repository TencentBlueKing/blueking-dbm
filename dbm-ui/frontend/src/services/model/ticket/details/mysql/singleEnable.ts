import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 单节点集群可用
 */
export interface SingleEnable extends DetailBase {
  cluster_ids: number[];
  clusters: DetailClusters;
  force: boolean;
}
