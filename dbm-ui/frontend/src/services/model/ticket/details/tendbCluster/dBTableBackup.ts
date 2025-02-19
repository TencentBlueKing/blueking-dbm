import type { DetailBase, DetailClusters } from '../common';

/**
 * TenDB Cluster 库表备份
 */
export interface DbTableBackup extends DetailBase {
  clusters: DetailClusters;
  infos: {
    backup_local: string;
    cluster_id: number;
    db_patterns: string[];
    ignore_dbs: string[];
    ignore_tables: string[];
    table_patterns: string[];
  }[];
}
