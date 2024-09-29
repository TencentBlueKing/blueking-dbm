import type { DetailBase, DetailClusters } from '../common';

/**
 * TenDB Cluster 全库备份
 */
export interface FullBackup extends DetailBase {
  clusters: DetailClusters;
  infos: {
    backup_type: string;
    clusters: {
      backup_local: string;
      cluster_id: number;
    }[];
    file_tag: string;
  };
}
