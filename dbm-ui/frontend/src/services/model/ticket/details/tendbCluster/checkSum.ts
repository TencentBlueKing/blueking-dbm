import type { DetailBase, DetailClusters } from '../common';

/**
 * TenDB Cluster 数据校验修复
 */

export interface CheckSum extends DetailBase {
  clusters: DetailClusters;
  data_repair: {
    is_repair: boolean;
    mode: string;
  };
  infos: {
    cluster_id: number;
    backup_infos: {
      master: string;
      slave: string;
      db_patterns: string[];
      ignore_dbs: string[];
      ignore_tables: string[];
      table_patterns: string[];
    };
    checksum_scope: string;
  }[];
  is_sync_non_innodb: boolean;
  runtime_hour: number;
  timing: string;
}
