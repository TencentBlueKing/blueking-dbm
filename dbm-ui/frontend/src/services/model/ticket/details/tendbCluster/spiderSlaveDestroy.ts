import type { DetailBase, DetailClusters } from '../common';

export interface SpiderSlaveDestroy extends DetailBase {
  cluster_ids: number[];
  clusters: DetailClusters;
  is_safe: boolean;
  old_nodes: {
    reduce_spider_slave_hosts: {
      bk_host_id: number;
      cluster_id: number;
      ip: string;
      port: number;
    }[];
  };
}
