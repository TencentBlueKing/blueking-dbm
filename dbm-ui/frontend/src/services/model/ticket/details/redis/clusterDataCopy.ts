import type { DetailBase, DetailClusters } from '../common';

export interface ClusterDataCopy extends DetailBase {
  clusters: DetailClusters;
  dts_copy_type: 'copy_to_other_system' | 'diff_app_diff_cluster' | 'one_app_diff_cluster' | 'user_built_to_dbm';
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
