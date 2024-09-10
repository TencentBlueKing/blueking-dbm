import type { DetailBase, DetailClusters } from '../common';

/**
 *  TenDB Cluster 添加运维节点
 */

export interface SpiderMntApply extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    bk_cloud_id: string;
    spider_ip_list: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
  }[];
}
