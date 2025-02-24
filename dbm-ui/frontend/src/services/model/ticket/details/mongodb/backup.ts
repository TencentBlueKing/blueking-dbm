import type { DetailBase, DetailClusters } from '../common';

export interface Backup extends DetailBase {
  backup_type?: string;
  clusters: DetailClusters;
  file_tag: string;
  infos: {
    backup_host: string;
    cluster_ids: number[];
    ns_filter: {
      db_patterns: string[];
      ignore_dbs: string[];
      ignore_tables: string[];
      table_patterns: string[];
    };
  }[];
}
