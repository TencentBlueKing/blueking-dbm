import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 添加从库
 */

export interface AddSlave extends DetailBase {
  backup_source: string;
  clusters: DetailClusters;
  infos: {
    cluster_ids: number[];
    new_slave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
  }[];
}
