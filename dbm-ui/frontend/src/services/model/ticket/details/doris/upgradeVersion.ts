import type { DetailBase, DetailClusters } from '../common';

export interface UpgradeVersion extends DetailBase {
  cluster_id: number;
  clusters?: DetailClusters;
  new_version: string;
}
