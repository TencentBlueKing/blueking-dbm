import type { ApplySpecInfo, DetailBase, DetailClusters } from '../common';

/**
 *  TenDB Cluster 扩容接入层
 */

export interface SpiderAddNodes extends DetailBase {
  clusters: DetailClusters;
  infos: {
    add_spider_role: string;
    cluster_id: number;
    resource_spec: {
      spider_ip_list: {
        count: number;
        spec_id: number;
      };
    };
  }[];
  ip_source: string;
  specs: Record<string, ApplySpecInfo>;
}
