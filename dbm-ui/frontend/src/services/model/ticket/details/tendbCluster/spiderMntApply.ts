import type { DetailBase, DetailClusters } from '../common';

/**
 *  TenDB Cluster 添加运维节点
 */

export interface SpiderMntApply extends DetailBase {
  clusters: DetailClusters;
  infos: {
    bk_cloud_id: string;
    cluster_id: number;
    spider_ip_list: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
  }[];
}
