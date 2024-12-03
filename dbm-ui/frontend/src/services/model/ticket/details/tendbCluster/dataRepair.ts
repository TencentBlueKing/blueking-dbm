import type { DetailBase, DetailClusters } from '../common';

/**
 * TenDBCluster 数据修复
 */
export interface DataRepair extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    master: {
      id: number;
      ip: string;
      port: number;
      bk_biz_id: number;
      bk_host_id: number;
      bk_cloud_id: number;
    };
    slaves: {
      id: number;
      ip: string;
      port: number;
      bk_biz_id: number;
      bk_host_id: number;
      bk_cloud_id: number;
      is_consistent: boolean;
    }[];
  }[];
  end_time: string;
  start_time: string;
  trigger_type: string;
  checksum_table: string;
  is_sync_non_innodb: boolean;
  is_ticket_consistent: boolean;
}
