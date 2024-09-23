import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 迁移主从
 */

export interface MigrateCluster extends DetailBase {
  backup_source: string;
  clusters: DetailClusters;
  infos: {
    cluster_ids: number[];
    new_master: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port?: number;
    };
    new_slave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port?: number;
    };
  }[];
  is_safe: boolean;
  ip_source: string;
}
