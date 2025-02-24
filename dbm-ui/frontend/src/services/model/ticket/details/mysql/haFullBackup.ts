import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 全库备份
 */
export interface HaFullBackup extends DetailBase {
  backup_type: 'logical' | 'physical';
  clusters: DetailClusters;
  file_tag: 'DBFILE1M' | 'DBFILE6M' | 'DBFILE1Y' | 'DBFILE3Y';
  infos: {
    backup_local: 'master' | 'slave';
    cluster_id: number;
  }[];
}
