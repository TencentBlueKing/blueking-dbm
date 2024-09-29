import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 添加Proxy
 */

interface MysqlIpItem extends DetailBase {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_host_id: number;
  ip: string;
  port?: number;
}

export interface ProxyAdd extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_ids: number[];
    new_proxy: MysqlIpItem;
  }[];
}
