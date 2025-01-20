import type { DetailBase, DetailClusters } from '../common';

export interface InstallModule extends DetailBase {
  clusters: DetailClusters;
  bk_cloud_id: number;
  infos: {
    cluster_id: number;
    db_version: string;
    load_modules: string[];
  }[];
}
