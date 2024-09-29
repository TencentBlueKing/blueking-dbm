import type { DetailBase, DetailClusters } from '../common';

export interface DatacopyCheckRepair extends DetailBase {
  clusters: DetailClusters;
  execute_mode: string;
  specified_execution_time: string; // 定时执行,指定执行时间
  check_stop_time: string; // 校验终止时间,
  keep_check_and_repair: boolean; // 是否一直保持校验
  data_repair_enabled: boolean; // 是否修复数据
  repair_mode: string;
  infos: [
    {
      bill_id: number; // 关联的(数据复制)单据ID
      src_cluster: string; // 源集群,来自于数据复制记录
      src_instances: string[]; // 源实例列表
      dst_cluster: string; // 目的集群,来自于数据复制记录
      key_white_regex: string; // 包含key
      key_black_regex: string; // 排除key
    },
  ];
}
