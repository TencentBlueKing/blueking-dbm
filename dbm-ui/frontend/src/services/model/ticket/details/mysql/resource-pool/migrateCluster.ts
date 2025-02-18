import type { DetailBase, DetailClusters } from '../../common';

/**
 * MySQL 迁移主从
 */

export interface MigrateCluster extends DetailBase {
  backup_source: string;
  clusters: DetailClusters;
  ip_source: 'resource_pool';
  infos: {
    cluster_ids: number[];
    resource_spec: {
      new_master: {
        spec_id: number;
        hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
          port: number;
        }[];
      };
      new_slave: {
        spec_id: number;
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
  is_safe: boolean;
}
