import type { DetailBase, DetailClusters } from '../common';

export interface KeysExtract extends DetailBase {
  delete_type: string;
  rules: {
    black_regex: string;
    cluster_id: number;
    domain: string;
    path: string;
    total_size: string;
    white_regex: string;
    create_at: string;
    target: string;
    backup_type: string;
  }[];
  clusters: DetailClusters;
}
