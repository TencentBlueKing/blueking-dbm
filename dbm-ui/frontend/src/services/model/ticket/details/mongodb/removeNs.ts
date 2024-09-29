import type { DetailBase, DetailClusters } from '../common';

export interface RemoveNs extends DetailBase {
  clusters: DetailClusters;
  is_safe: boolean;
  infos: {
    cluster_ids: number[];
    drop_index: boolean;
    drop_type: string;
    ns_filter: {
      db_patterns: string[];
      ignore_dbs: string[];
      ignore_tables: string[];
      table_patterns: string[];
    };
  }[];
}
