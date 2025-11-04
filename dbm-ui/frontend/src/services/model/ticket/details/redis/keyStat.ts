import type { DetailBase, DetailClusters } from '../common';

export interface KeyStat extends DetailBase {
  bk_cloud_id: number;
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    cluster_type: string;
    immute_domain: string;
    ins: {
      addr: string;
      key_num: number; // 展示用
      memory_total: number; // 展示用
    }[];
  }[];
}
