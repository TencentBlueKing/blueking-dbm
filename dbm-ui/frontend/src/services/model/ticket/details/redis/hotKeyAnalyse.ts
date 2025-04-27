import type { DetailBase, DetailClusters } from '../common';

export interface HotKeyAnalyse extends DetailBase {
  analysis_time: number;
  bk_cloud_id: number;
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    cluster_type: string;
    immute_domain: string;
    ins: string[];
  }[];
}
