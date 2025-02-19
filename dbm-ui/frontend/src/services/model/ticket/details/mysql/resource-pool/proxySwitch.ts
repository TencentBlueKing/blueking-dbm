import type { ResourcePoolDetailBase } from '../../common';

/**
 * MySQL 替换Proxy
 */

export interface ProxySwitch extends ResourcePoolDetailBase {
  force: boolean;
  infos: {
    cluster_ids: number[];
    display_info: {
      related_clusters: string[];
      related_instances: string[];
      type: 'INSTANCE_REPLACE' | 'HOST_REPLACE';
    };
    old_nodes: {
      origin_proxy: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
      }[];
    };
    resource_spec: {
      target_proxy: {
        hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
          port: number;
        }[];
      };
    };
  }[];
}
