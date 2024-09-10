import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 全库备份
 */
export interface HaFullBackup extends DetailBase {
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
