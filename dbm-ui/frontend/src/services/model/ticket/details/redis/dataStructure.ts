import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface DataStructure extends DetailBase {
  clusters: DetailClusters;
  infos: {
    bk_cloud_id: number;
    cluster_id: number;
    master_instances: string[];
    recovery_time_point: string;
    resource_spec: {
      redis: {
        count: number;
        label_names: string[];
        labels: string[];
        spec_id: number;
      };
    };
  }[];
  ip_source: 'resource_pool';
  specs: DetailSpecs;
}
