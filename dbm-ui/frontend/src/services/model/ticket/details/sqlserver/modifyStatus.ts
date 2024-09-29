import type { DetailBase, DetailClusters } from '../common';

export interface ModifyStatus extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    ip_list: string[];
  }[];
}
