import type { DetailBase, DetailClusters } from '../common';

export interface VersionUpdateOnline extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_ids: number[];
    current_versions: string[];
    node_type: string;
    target_version: string;
  }[];
}
