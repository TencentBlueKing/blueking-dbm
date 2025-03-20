import type { ResourcePoolDetailBase } from '../../common';

export interface SpiderMntDestroy extends ResourcePoolDetailBase {
  infos: {
    cluster_id: number;
    old_nodes: {
      spider_ip_list: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
    };
  }[];
  is_safe: boolean;
}
