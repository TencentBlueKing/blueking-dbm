import type { DetailBase, DetailClusters } from '../common';

export interface ProxyUpgrade extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_ids: number[];
    display_info: {
      current_version: string | string[];
      target_package: string;
    };
    pkg_id: number;
  }[];
  is_check_process: boolean;
}
