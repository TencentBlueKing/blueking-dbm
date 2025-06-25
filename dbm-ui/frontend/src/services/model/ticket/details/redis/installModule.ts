import type { DetailBase, DetailClusters } from '../common';

export interface InstallModule extends DetailBase {
  bk_cloud_id: number;
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    db_version: string;
    load_modules: string[];
  }[];
}
