import type { DetailBase, DetailClusters } from '../common';

/**
 * TenDB Cluster 全库备份
 */
export interface FullBackup extends DetailBase {
  backup_type: string;
  clusters: DetailClusters;
  file_tag: string;
  infos: {
    cluster_id: number;
    backup_local: string;
  }[];
}
