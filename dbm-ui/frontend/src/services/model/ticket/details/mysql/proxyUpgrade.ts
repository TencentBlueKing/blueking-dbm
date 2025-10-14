import type { DetailBase, DetailClusters } from '../common';

export interface ProxyUpgrade extends DetailBase {
  clusters: DetailClusters;
  is_check_process: boolean;
  infos: {
    cluster_ids: number[];
    display_info: {
      current_version: string;
      target_package: string;
    };
    pkg_id: number;
  }[];
}
