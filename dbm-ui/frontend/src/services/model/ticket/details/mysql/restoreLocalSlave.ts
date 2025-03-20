import type { BackupSourceType } from '@services/types';

import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL Slave原地重建
 */

export interface RestoreLocalSlave extends DetailBase {
  backup_source: BackupSourceType;
  clusters: DetailClusters;
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
