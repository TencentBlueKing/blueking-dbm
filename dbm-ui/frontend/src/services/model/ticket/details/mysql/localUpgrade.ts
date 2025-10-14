import type { DetailBase, DetailClusters } from '../common';

export interface LocalUpgrade extends DetailBase {
  clusters: DetailClusters;
  is_check_process: boolean;
  is_verify_checksum?: boolean; // 主从集群传递
  infos: {
    cluster_ids: number[];
    display_info: {
      charset: string;
      cluster_type: string;
      current_module_name: string;
      current_package: string;
      current_version: string;
      target_module_name?: string; // 单节点集群传递
      target_package: string;
      target_version?: string; // 单节点集群传递
    };
    new_db_module_id?: number; // 单节点集群传递
    pkg_id: number;
  }[];
}
