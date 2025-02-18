import type { DetailBase, DetailClusters } from '../../common';

/**
 * MySQL 替换Proxy
 */

export interface ProxySwitch extends DetailBase {
  clusters: DetailClusters;
  force: boolean;
  ip_source: 'resource_pool';
  infos: {
    cluster_ids: number[];
    display_info: {
      type: 'INSTANCE_REPLACE' | 'HOST_REPLACE';
      related_clusters: string[];
      related_instances: string[];
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
