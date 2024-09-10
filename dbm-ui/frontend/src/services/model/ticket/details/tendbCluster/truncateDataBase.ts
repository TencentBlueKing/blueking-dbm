import type { DetailBase, DetailClusters } from '../common';

/**
 *  TenDB Cluster 清档
 */

export interface TruncateDataBase extends DetailBase {
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
