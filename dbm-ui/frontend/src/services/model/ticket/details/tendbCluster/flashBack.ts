import type { DetailBase, DetailClusters } from '../common';

/**
 * TenDB Cluster 闪回
 */

export interface FlashBack extends DetailBase {
  clusters: DetailClusters;
  flashback_type: 'TABLE_FLASHBACK' | 'RECORD_FLASHBACK';
  force: boolean;
  infos: {
    cluster_id: number;
    databases: string[];
    databases_ignore: string[];
    direct_write_back: boolean;
    end_time: string;
    message: string;
    mysqlbinlog_rollback: string;
    recored_file: string;
    rows_filter: string;
    start_time: string;
    tables: string[];
    tables_ignore: string[];
  }[];
}
