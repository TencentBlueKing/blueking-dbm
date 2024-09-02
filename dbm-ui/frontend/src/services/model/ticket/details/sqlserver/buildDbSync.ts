import type { DetailBase, DetailClusters } from '../common';

export interface BuildDbSync extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    sync_dbs: string[];
  }[];
}
