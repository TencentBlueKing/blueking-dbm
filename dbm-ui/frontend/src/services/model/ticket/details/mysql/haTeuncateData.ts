import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 高可用清档
 */

export interface HaTeuncateData extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    db_patterns: [];
    ignore_dbs: [];
    ignore_tables: [];
    table_patterns: [];
    force: boolean;
    truncate_data_type: string;
  }[];
}
