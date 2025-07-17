import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 缩容Proxy
 */
export interface ProxyReduce extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_ids: number[];
    old_nodes: {
      origin_proxy: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
    };
    origin_proxy_ip: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
  }[];
  is_safe: boolean;
}
