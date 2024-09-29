import type { DetailBase, DetailClusters } from '../common';

/**
 * TenDB Cluster 主库故障切换
 */

export interface MasterFailOver extends DetailBase {
  clusters: DetailClusters;
  force: boolean;
  is_check_process: boolean;
  is_verify_checksum: boolean;
  is_check_delay: boolean;
  infos: {
    cluster_id: number;
    switch_tuples: {
      master: {
        ip: string;
        bk_cloud_id: number;
        bk_host_id: number;
        bk_biz_id: number;
      };
      slave: {
        ip: string;
        bk_cloud_id: number;
        bk_host_id: number;
        bk_biz_id: number;
      };
    }[];
  }[];
}
