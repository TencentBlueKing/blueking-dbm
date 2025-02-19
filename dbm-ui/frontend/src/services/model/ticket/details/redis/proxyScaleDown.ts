import type { DetailBase, DetailClusters } from '../common';

export interface ProxyScaleDown extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    online_switch_type: 'user_confirm' | 'no_confirm';
    proxy_reduced_hosts?: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
    target_proxy_count?: number;
  }[];
  ip_source: 'resource_pool';
}
