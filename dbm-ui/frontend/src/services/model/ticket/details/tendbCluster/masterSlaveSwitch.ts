import type { DetailBase, DetailClusters } from '../common';

/**
 * TenDB Cluster 主从互切
 */

export interface MasterSlaveSwitch extends DetailBase {
  clusters: DetailClusters;
  force: boolean; // 互切单据就传False，表示安全切换
  is_check_process: boolean;
  is_verify_checksum: boolean;
  is_check_delay: boolean; // 目前互切单据延时属于强制检测，故必须传True， 用户没有选择
  infos: {
    cluster_id: number;
    switch_tuples: {
      master: {
        ip: string;
        bk_cloud_id: number;
        bk_host_id: number;
      };
      slave: {
        ip: string;
        bk_cloud_id: number;
        bk_host_id: number;
      };
    }[];
  }[];
}
