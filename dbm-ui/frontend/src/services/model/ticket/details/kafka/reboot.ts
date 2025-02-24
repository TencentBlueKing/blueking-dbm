import type { DetailBase, DetailClusters } from '../common';

export interface Reboot extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
  instance_list: {
    bk_cloud_id: number;
    bk_host_id: number;
    instance_id: number;
    instance_name: string;
    ip: string;
    port: number;
  }[];
}
