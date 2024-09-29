import type { DetailBase, DetailClusters } from '../common';

/**
 * TenDB Cluster 数据校验修复
 */

export interface CheckSum extends DetailBase {
  checksum_table: string;
  clusters: DetailClusters;
  data_repair: {
    is_repair: boolean;
    mode: string;
  };
  infos: {
    backup_infos: {
      db_patterns: string[];
      ignore_tables: string[];
      ignore_dbs: string[];
      master: string;
      slave: string;
      table_patterns: string[];
    }[];
    checksum_scope: string;
    cluster_id: number;
  }[];
  is_consistent_list: Record<string, boolean>;
  is_sync_non_innodb: boolean;
  runtime_hour: number;
  timing: string;
}
