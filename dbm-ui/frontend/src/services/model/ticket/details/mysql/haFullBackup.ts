import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 全库备份
 */
export interface HaFullBackup extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    backup_local: 'master' | 'slave';
  }[];
  file_tag: 'DBFILE1M' | 'DBFILE6M' | 'DBFILE1Y' | 'DBFILE3Y';
  backup_type: 'logical' | 'physical';
}
