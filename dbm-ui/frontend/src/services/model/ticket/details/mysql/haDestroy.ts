import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 主从集群销毁
 */
export interface HaDestroy extends DetailBase {
  force: boolean;
  clusters: DetailClusters;
  cluster_ids: number[];
}
