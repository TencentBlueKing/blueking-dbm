import type { DetailBase, DetailClusters } from '../common';

export interface ClusterRollbackDataCopy extends DetailBase {
  clusters: DetailClusters;
  //  dts 复制类型: 回档临时实例数据回写
  dts_copy_type: 'copy_from_rollback_instance';
  write_mode: string;
  infos: {
    src_cluster: string; // 构造产物访问入口
    dst_cluster: number;
    key_white_regex: string; // 包含key
    key_black_regex: string; // 排除key
    recovery_time_point: string; // 构造到指定时间
  }[];
}
