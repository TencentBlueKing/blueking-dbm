import type { DetailBase, DetailClusters } from '../common';

/**
 * TenDB Cluster 全库备份
 */
export interface FullBackup extends DetailBase {
  backup_type: string;
  clusters: DetailClusters;
  file_tag: string;
  infos: {
    backup_local: string;
    cluster_id: number;
  }[];
}
