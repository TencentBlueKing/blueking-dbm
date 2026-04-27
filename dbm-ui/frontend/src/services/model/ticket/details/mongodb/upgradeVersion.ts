import type { DetailBase, DetailClusters } from '../common';

export interface UpgradeVersion extends DetailBase {
  bk_cloud_id: number;
  clusters: DetailClusters;
  infos: {
    bk_cloud_id: number;
    cluster_id_list: number[];
    current_version: string;
    dest_version: string;
    strategy: 'rolling' | 'full_stop';
  }[];
}
