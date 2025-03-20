import type { DetailBase, DetailClusters } from '../common';

export interface ScaleIn extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
  ip_source: 'manual_input' | 'resource_pool';
  nodes?: {
    riak: Array<{
      alive: number;
      bk_cloud_id: number;
      bk_disk: number;
      bk_host_id: number;
      ip: string;
    }>;
  };
  resource_spec: {
    riak: {
      count: number;
      spec_id: number;
    };
  };
}
