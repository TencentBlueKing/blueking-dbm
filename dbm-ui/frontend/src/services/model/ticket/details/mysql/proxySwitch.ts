import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 替换Proxy
 */

export interface ProxySwitch extends DetailBase {
  clusters: DetailClusters;
  force: boolean;
  infos: {
    cluster_ids: number[];
    display_info: {
      type: 'INSTANCE_REPLACE' | 'HOST_REPLACE';
      related_clusters: string[];
      related_instances: string[];
    };
    origin_proxy: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port?: number;
    };
    target_proxy: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port?: number;
    };
  }[];
  ip_source: string;
}
