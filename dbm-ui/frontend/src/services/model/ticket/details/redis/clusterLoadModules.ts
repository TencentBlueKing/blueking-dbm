import type { DetailBase, DetailClusters } from '../common';

export interface ClusterLoadModules extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    dv_version: string;
    load_modules: string[];
  }[];
}
