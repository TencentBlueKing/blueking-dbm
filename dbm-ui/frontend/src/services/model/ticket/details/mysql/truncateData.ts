import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 清档
 */

export interface TruncateData extends DetailBase {
  clear_mode: {
    days: 7 | 15;
    mode: 'timer' | 'manual';
  };
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    db_patterns: [];
    force: boolean;
    ignore_dbs: [];
    ignore_tables: [];
    table_patterns: [];
    truncate_data_type: string;
  }[];
}
