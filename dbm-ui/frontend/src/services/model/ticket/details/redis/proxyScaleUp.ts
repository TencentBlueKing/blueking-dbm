import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface ProxyScaleUp extends DetailBase {
  clusters: DetailClusters;
  ip_source: 'resource_pool';
  infos: {
    cluster_id: number;
    bk_cloud_id: number;
    target_proxy_count: number;
    resource_spec: {
      proxy: {
        spec_id: number;
        count: number;
      };
    };
  }[];
  specs: DetailSpecs;
}
