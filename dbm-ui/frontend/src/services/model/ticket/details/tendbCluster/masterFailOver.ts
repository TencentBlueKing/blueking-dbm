import type { DetailBase, DetailClusters } from '../common';

/**
 * TenDB Cluster 主库故障切换
 */

export interface MasterFailOver extends DetailBase {
  clusters: DetailClusters;
  force: boolean;
  infos: {
    cluster_id: number;
    switch_tuples: {
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
  }[];
  is_check_delay: boolean;
  is_check_process: boolean;
  is_verify_checksum: boolean;
}
