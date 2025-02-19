import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 清档
 */

export interface TruncateData extends DetailBase {
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
