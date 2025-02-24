import type { DetailBase, DetailClusters } from '../common';

export interface KeysDelete extends DetailBase {
  clusters: DetailClusters;
  delete_type: string;
  rules: {
    backup_type: string;
    black_regex: string;
    cluster_id: number;
    create_at: string;
    domain: string;
    path: string;
    target: string;
    total_size: string;
    white_regex: string;
  }[];
}
