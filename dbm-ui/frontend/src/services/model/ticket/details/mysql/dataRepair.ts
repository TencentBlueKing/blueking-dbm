import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 数据修复
 */
export interface DataRepair extends DetailBase {
  checksum_table: string;
  clusters: DetailClusters;
  end_time: string;
  infos: {
    cluster_id: number;
    master: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      id: number;
      ip: string;
      port: number;
    };
    slaves: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      id: number;
      ip: string;
      is_consistent: boolean;
      port: number;
    }[];
  }[];
  is_sync_non_innodb: boolean;
  is_ticket_consistent: boolean;
  start_time: string;
  trigger_type: string;
}
