import type { DetailBase, DetailClusters } from '../common';

export interface DataMigrate extends DetailBase {
  clusters: DetailClusters;
  dts_mode: string;
  infos: {
    db_list: string[];
    dst_cluster: number;
    dts_id: number;
    ignore_db_list: string[];
    rename_infos: {
      db_name: string;
      old_db_name: string;
      target_db_name: string;
    }[];
    src_cluster: number;
  }[];
  manual_terminate: boolean;
  need_auto_rename: boolean;
}
