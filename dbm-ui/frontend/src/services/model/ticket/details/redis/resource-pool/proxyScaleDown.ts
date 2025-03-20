import type { ResourcePoolDetailBase } from '../../common';

export interface ProxyScaleDown extends ResourcePoolDetailBase {
  infos: {
    cluster_id: number;
    old_nodes: {
      proxy_reduced_hosts: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
    };
    online_switch_type: 'user_confirm' | 'no_confirm';
    target_proxy_count: number;
  }[];
}
