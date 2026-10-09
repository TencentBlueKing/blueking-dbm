import type { DetailBase, DetailClusters } from '../common';

export interface Purge extends DetailBase {
  clusters: DetailClusters;
  delete_type: string;
  rules: {
    backup: boolean;
    cluster_id: number;
    cluster_type: string;
    db_list: number[];
    domain: string;
    flushall: boolean;
    force: boolean;
  }[];
}
