import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL DB 数据克隆
 */

export interface DataMigrate extends DetailBase {
  clusters: DetailClusters;
  infos: {
    clone_db_list: string[];
    data_schema_grant: string;
    db_list: string[];
    ignore_db_list: string[];
    source_cluster: number;
    target_clusters: number[];
  }[];
}
