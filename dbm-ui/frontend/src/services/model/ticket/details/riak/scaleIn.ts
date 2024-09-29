import type { DetailBase, DetailClusters } from '../common';

export interface ScaleIn extends DetailBase {
  clusters: DetailClusters;
  cluster_id: number;
  ip_source: 'manual_input' | 'resource_pool';
  resource_spec: {
    riak: {
      count: number;
      spec_id: number;
    };
  };
  nodes?: {
    riak: Array<{
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      alive: number;
      bk_disk: number;
    }>;
  };
}
