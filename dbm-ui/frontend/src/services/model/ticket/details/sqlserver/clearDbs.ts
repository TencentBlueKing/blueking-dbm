import type { DetailBase, DetailClusters } from '../common';

export interface ClearDbs extends DetailBase {
  clusters: DetailClusters;
  infos: {
    clean_dbs: string[];
    clean_dbs_patterns: string[];
    clean_ignore_dbs_patterns: string[];
    clean_mode: string;
    clean_tables: string[];
    cluster_id: number;
    ignore_clean_tables: string[];
  }[];
  is_safe: boolean;
}
