import type { DetailBase, DetailClusters } from '../common';

export interface ProxyUpgrade extends DetailBase {
  clusters: DetailClusters;
  infos: {
    pkg_id: string;
    cluster_ids: number[];
    display_info: {
      current_version: string;
    };
  }[];
  force: boolean;
}
