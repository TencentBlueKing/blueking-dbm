import type { DetailBase, DetailClusters } from '../common';

export interface ProxyScaleDown extends DetailBase {
  clusters: DetailClusters;
  ip_source: 'resource_pool';
  infos: {
    cluster_id: number;
    target_proxy_count?: number;
    proxy_reduced_hosts?: {
      ip: string;
      bk_host_id: number;
      bk_cloud_id: number;
      bk_biz_id: number;
    }[];
    online_switch_type: 'user_confirm' | 'no_confirm';
  }[];
}
