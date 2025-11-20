import type { DetailBase, DetailClusters } from '../common';

export interface ClusterReinstallDbmon extends DetailBase {
  bk_biz_id: number;
  bk_cloud_id: number;
  cluster_ids: number[];
  clusters: DetailClusters;
  is_stop: boolean;
  restart_exporter: boolean;
}
