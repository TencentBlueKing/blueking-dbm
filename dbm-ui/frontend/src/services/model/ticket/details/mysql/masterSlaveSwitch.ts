import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 主从互换
 */

export interface MasterSlaveSwitch extends DetailBase {
  backup_source: string;
  clusters: DetailClusters;
  force: boolean;
  infos: {
    cluster_ids: number[];
    slave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port?: number;
    };
  }[];
}
