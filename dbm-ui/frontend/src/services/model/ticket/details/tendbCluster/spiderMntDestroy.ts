import type { DetailBase, DetailClusters } from '../common';

export interface SpiderMntDestroy extends DetailBase {
  is_safe: boolean;
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    spider_ip_list: {
      ip: string;
      bk_cloud_id: number;
    }[];
  }[];
}
