import type { DetailBase, DetailClusters } from '../common';

/**
 *  Mysql 集群标准化
 */
export interface ClusterStandardize extends DetailBase {
  bk_biz_id: number;
  cluster_ids: number[];
  clusters: DetailClusters;
  with_cc_standardize: boolean; // 是否cc模块标准
  with_deploy_binary: boolean; // 是否推送二进制
  with_instance_standardize: boolean; // 是否实例标准化. 高危
  with_push_config: boolean; // 是否推送配置
}
