import type { DetailBase, DetailClusters } from '../common';

export interface ClusterDataCopy extends DetailBase {
  clusters: DetailClusters;
  data_check_repair_setting: {
    execution_frequency: string;
    type: string;
  };
  dts_copy_type: 'copy_to_other_system' | 'diff_app_diff_cluster' | 'one_app_diff_cluster' | 'user_built_to_dbm';
  infos: {
    dst_bk_biz_id: number;
    dst_cluster: number;
    key_black_regex: string; // 排除key
    key_white_regex: string; // 包含key
    src_cluster: number;
    src_cluster_password: string;
    src_cluster_type: string;
  }[];
  sync_disconnect_setting: {
    reminder_frequency: string;
    type: string;
  };
  write_mode: string;
}
