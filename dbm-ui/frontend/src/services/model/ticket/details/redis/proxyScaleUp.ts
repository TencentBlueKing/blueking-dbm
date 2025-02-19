import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface ProxyScaleUp extends DetailBase {
  clusters: DetailClusters;
  infos: {
    bk_cloud_id: number;
    cluster_id: number;
    resource_spec: {
      proxy: {
        count: number;
        spec_id: number;
      };
    };
    target_proxy_count: number;
  }[];
  ip_source: 'resource_pool';
  specs: DetailSpecs;
}
