import type { DetailBase, DetailClusters } from '../common';

export interface SpiderMntDestroy extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    spider_ip_list: {
      bk_cloud_id: number;
      ip: string;
    }[];
  }[];
  is_safe: boolean;
}
