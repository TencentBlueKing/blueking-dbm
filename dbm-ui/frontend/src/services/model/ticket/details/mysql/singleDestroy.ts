import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 单节点集群销毁
 */
export interface SingleDestroy extends DetailBase {
  force: boolean;
  clusters: DetailClusters;
  cluster_ids: number[];
}
