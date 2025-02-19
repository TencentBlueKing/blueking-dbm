import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface ClusterAddSlave extends DetailBase {
  clusters: DetailClusters;
  infos: {
    bk_cloud_id: number;
    cluster_id?: number; // 旧协议，兼容旧单据用
    cluster_ids: number[];
    pairs: {
      redis_master: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      };
      redis_slave: {
        count: number;
        old_slave_ip: string;
        spec_id: number;
      };
    }[];
  }[];
  ip_source: 'resource_pool';
  specs: DetailSpecs;
}
