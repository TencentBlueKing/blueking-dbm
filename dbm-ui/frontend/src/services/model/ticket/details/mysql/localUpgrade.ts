import type { DetailBase, DetailClusters } from '../common';

export interface LocalUpgrade extends DetailBase {
  clusters: DetailClusters;
  infos: {
    pkg_id: number;
    cluster_ids: number[];
    new_db_module_id?: number; // 单节点集群传递
    display_info: {
      cluster_type: string;
      current_version: string;
      current_package: string;
      target_package: string;
      charset: string;
      current_module_name: string;
      target_version?: string; // 单节点集群传递
      target_module_name?: string; // 单节点集群传递
    };
  }[];
  force: boolean;
}
