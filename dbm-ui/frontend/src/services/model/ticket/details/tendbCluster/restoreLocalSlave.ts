import type { DetailBase, DetailClusters } from '../common';

/**
 *  TenDB Cluster Slave原地重建
 */

export interface RestoreLocalSlave extends DetailBase {
  backup_source: string;
  clusters: DetailClusters;
  force: boolean;
  infos: {
    cluster_id: number;
    slave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port: number;
    };
  }[];
}
