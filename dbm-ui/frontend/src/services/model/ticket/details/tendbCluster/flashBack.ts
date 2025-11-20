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
    conv_rows_update_to_write: boolean;
    filter_delete_rows_only: boolean;
    rows_filter: string;
    start_time: string;
    tables: string[];
    tables_ignore: string[];
  }[];
}
