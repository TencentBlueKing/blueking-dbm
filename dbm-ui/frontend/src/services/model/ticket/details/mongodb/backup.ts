import type { DetailBase, DetailClusters } from '../common';

export interface Backup extends DetailBase {
  clusters: DetailClusters;
  file_tag: string;
  backup_type?: string;
  infos: {
    cluster_ids: number[];
    backup_host: string;
    ns_filter: {
      db_patterns: string[];
      ignore_dbs: string[];
      ignore_tables: string[];
      table_patterns: string[];
    };
  }[];
}
