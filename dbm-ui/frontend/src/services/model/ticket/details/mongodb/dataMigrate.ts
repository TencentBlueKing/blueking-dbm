import type { DetailBase, DetailClusters } from '../common';

export interface DataMigrate extends DetailBase {
  clusters: DetailClusters;
  infos: {
    backup_ticket_id?: number;
    ns_filter?: {
      db_patterns: string[];
      ignore_dbs: string[];
      ignore_tables: string[];
      table_patterns: string[];
    } | null;
    source_cluster_id: number;
    source_mode: 'backup_ticket' | 'cluster';
    target_cluster_id: number;
  }[];
}
