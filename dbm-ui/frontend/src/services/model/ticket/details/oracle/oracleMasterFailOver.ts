import type { DetailBase, DetailClusters } from '../common';

/**
 * Oracle 主库故障切换
 */
export interface oracleMasterFailOver extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    master: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
    slave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
  }[];
  is_check_process: boolean;
}
