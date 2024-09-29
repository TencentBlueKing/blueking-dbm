import type { DetailBase } from '../common';

export interface SpiderSlaveDestroy extends DetailBase {
  is_safe: boolean;
  cluster_ids: number[];
}
