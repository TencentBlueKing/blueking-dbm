import type { ResourcePoolDetailBase } from '../../common';

/**
 * TenDB Cluster 缩容接入层
 */

export interface SpiderReduceNodes extends ResourcePoolDetailBase {
  infos: {
    cluster_id: number;
    old_nodes: {
      spider_reduced_hosts: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
    };
    reduce_spider_role: string;
    spider_reduced_to_count: number;
  }[];
  is_safe: boolean; // 是否做安全检测
}
