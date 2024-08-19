import type { DetailBase, DetailClusters } from '../common';

export interface Rollback extends DetailBase {
  clusters: DetailClusters;
  infos: {
    db_list: string[];
    dst_cluster: number;
    ignore_db_list: string[];
    rename_infos: {
      db_name: string;
      old_db_name: string;
      rename_db_name: string;
      target_db_name: string;
    }[];
    restore_backup_file: {
      backup_id: string;
      logs: Record<string, string>[];
    };
    src_cluster: number;
  }[];
}
