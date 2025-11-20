import type { DetailBase, DetailClusters } from '../common';

export interface RemoteUpgrade extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    current_version: {
      charset: string;
      db_module_name: string;
      db_version: string;
      pkg_name: string;
    };
    new_db_module_id: number;
    pkg_id: number;
    target_version: {
      charset: string;
      db_module_name: string;
      db_version: string;
      pkg_name: string;
    };
  }[];
  is_check_process: boolean;
  upgrade_local: boolean;
}
