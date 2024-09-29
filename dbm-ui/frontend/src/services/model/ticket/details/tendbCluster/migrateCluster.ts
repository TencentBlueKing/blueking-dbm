import type { DetailBase, DetailClusters } from '../common';

/**
 * TenDB Cluster 主从迁移
 */

interface IHost {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_host_id: number;
  ip: string;
}

export interface MigrateCluster extends DetailBase {
  backup_source: string;
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    new_master: IHost;
    new_slave: IHost;
    old_master: IHost;
    old_slave: IHost;
  }[];
  ip_source: string;
  is_safe: boolean;
}
