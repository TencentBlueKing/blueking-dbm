import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 主库故障切换
 */

export interface MasterFailOver extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_ids: number[];
    master_ip: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port?: number;
    };
    slave_ip: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port?: number;
    };
  }[];
  is_check_delay: boolean;
  is_check_process: boolean;
  is_safe: boolean;
  is_verify_checksum: boolean;
}
