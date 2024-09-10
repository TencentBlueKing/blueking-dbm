import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL DB克隆
 */

export interface DataMigrate extends DetailBase {
  clusters: DetailClusters;
  infos: {
    db_list: string[];
    source_cluster: number;
    target_clusters: number[];
  }[];
}
