import type { DetailBase, DetailClusters } from '../common';

/**
 * TenDB Cluster 主库故障实例切换
 */

export interface InstanceFailOver extends DetailBase {
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
        port: number;
      };
      slave: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
      };
    }[];
  }[];
  is_check_delay: boolean;
  is_check_process: boolean;
  is_verify_checksum: boolean;
}
