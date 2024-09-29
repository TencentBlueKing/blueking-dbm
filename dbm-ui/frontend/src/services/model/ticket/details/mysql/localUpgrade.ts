import type { DetailBase, DetailClusters } from '../common';

export interface LocalUpgrade extends DetailBase {
  clusters: DetailClusters;
  infos: {
    pkg_id: number;
    cluster_ids: number[];
    display_info: {
      cluster_type: string;
      current_version: string;
      current_package: string;
      target_package: string;
      charset: string;
      current_module_name: string;
    };
  }[];
  force: boolean;
}
