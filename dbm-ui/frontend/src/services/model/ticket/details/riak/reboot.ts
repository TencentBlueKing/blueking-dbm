import type { DetailBase, DetailClusters } from '../common';

export interface Reboot extends DetailBase {
  bk_cloud_id: number;
  bk_host_id: number;
  cluster_id: number;
  clusters: DetailClusters;
  ip: string;
}
