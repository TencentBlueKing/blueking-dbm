import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface DataStructure extends DetailBase {
  clusters: DetailClusters;
  ip_source: 'resource_pool';
  infos: {
    cluster_id: number;
    bk_cloud_id: number;
    master_instances: string[];
    recovery_time_point: string;
    resource_spec: {
      redis: {
        spec_id: number;
        count: number;
      };
    };
  }[];
  specs: DetailSpecs;
}
