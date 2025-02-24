import type { DetailBase, DetailClusters } from '../common';

/**
 * TenDB Cluster 缩容接入层
 */

export interface SpiderReduceNodes extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    reduce_spider_role: string;
    spider_reduced_hosts?: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
    spider_reduced_to_count: number;
  }[];
  is_safe: boolean; // 是否做安全检测
}
