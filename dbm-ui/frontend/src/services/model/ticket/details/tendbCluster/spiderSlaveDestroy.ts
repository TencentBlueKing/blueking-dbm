import type { DetailBase, DetailClusters } from '../common';

export interface SpiderSlaveDestroy extends DetailBase {
  cluster_ids: number[];
  clusters: DetailClusters;
  is_safe: boolean;
}
