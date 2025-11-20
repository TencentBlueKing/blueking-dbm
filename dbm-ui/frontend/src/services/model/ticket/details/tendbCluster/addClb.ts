import type { DetailBase, DetailClusters } from '../common';

export interface AddClb extends DetailBase {
  bk_cloud_id: number;
  cluster_id: number;
  clusters: DetailClusters;
  spider_role: string; // spider_master / spider_slave'
}
