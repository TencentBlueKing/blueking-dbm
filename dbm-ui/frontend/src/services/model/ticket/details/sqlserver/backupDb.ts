import type { DetailBase, DetailClusters } from '../common';

export interface BackupDb extends DetailBase {
  backup_place: string;
  backup_type: string;
  clusters: DetailClusters;
  file_tag: string;
  infos: {
    backup_dbs: string[];
    cluster_id: number;
    db_list: string[];
    ignore_db_list: string[];
  }[];
  is_safe: boolean;
}
