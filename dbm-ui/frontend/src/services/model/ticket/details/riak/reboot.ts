import type { DetailBase, DetailClusters } from '../common';

export interface Reboot extends DetailBase {
  clusters: DetailClusters;
  cluster_id: number;
  bk_cloud_id: number;
  bk_host_id: number;
  ip: string;
}
