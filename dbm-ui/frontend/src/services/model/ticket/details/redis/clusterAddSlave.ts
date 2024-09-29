import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface ClusterAddSlave extends DetailBase {
  clusters: DetailClusters;
  ip_source: 'resource_pool';
  infos: {
    cluster_id?: number; // 旧协议，兼容旧单据用
    cluster_ids: number[];
    bk_cloud_id: number;
    pairs: {
      redis_master: {
        ip: string;
        bk_cloud_id: number;
        bk_host_id: number;
      };
      redis_slave: {
        spec_id: number;
        count: number;
        old_slave_ip: string;
      };
    }[];
  }[];
  specs: DetailSpecs;
}
