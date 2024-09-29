import type { DetailBase, DetailClusters } from '../common';

export interface ClusterDataCopy extends DetailBase {
  clusters: DetailClusters;
  dts_copy_type: string;
  write_mode: string;
  sync_disconnect_setting: {
    type: string;
    reminder_frequency: string;
  };
  data_check_repair_setting: {
    type: string;
    execution_frequency: string;
  };
  infos: {
    src_cluster: number;
    dst_cluster: number;
    key_white_regex: string; // 包含key
    key_black_regex: string; // 排除key
    src_cluster_type: string;
    src_cluster_password: string;
    dst_bk_biz_id: number;
  }[];
}
