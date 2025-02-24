import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 主从集群销毁
 */
export interface HaDestroy extends DetailBase {
  cluster_ids: number[];
  clusters: DetailClusters;
  force: boolean;
}
