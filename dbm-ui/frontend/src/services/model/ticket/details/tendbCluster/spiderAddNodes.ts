import type { DetailBase, DetailClusters, SpecInfo } from '../common';

/**
 *  TenDB Cluster 扩容接入层
 */

export interface SpiderAddNodes extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    add_spider_role: string;
    resource_spec: {
      spider_ip_list: {
        count: number;
        spec_id: number;
      };
    };
  }[];
  ip_source: string;
  specs: Record<string, SpecInfo>;
}
