import type { DetailBase, DetailClusters } from '../common';

/**
 * TenDB Cluster 缩容接入层
 */

export interface SpiderReduceNodes extends DetailBase {
  clusters: DetailClusters;
  is_safe: boolean; // 是否做安全检测
  infos: {
    cluster_id: number;
    reduce_spider_role: string;
    spider_reduced_to_count: number;
    spider_reduced_hosts?: {
      ip: string;
      bk_host_id: number;
      bk_cloud_id: number;
      bk_biz_id: number;
    }[];
  }[];
}
