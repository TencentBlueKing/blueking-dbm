import type { DetailBase, DetailClusters } from '../common';

export interface Disable extends DetailBase {
  cluster_ids: number[];
  clusters: DetailClusters;
  force: boolean;
  is_only_add_slave_domain: boolean;
  is_only_delete_slave_domain: boolean;
}
