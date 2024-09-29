import type { DetailBase, DetailClusters } from '../common';

export interface ProxyUpgrade extends DetailBase {
  clusters: DetailClusters;
  force: boolean;
  infos: {
    pkg_id: string;
    cluster_ids: number[];
    display_info: {
      current_version: string;
      target_package: string;
    };
  }[];
}
