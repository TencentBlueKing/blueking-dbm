import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 库表备份
 */
export interface HaDBTableBackup extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    db_patterns: string[];
    ignore_dbs: string[];
    ignore_tables: string[];
    table_patterns: string[];
  }[];
}
