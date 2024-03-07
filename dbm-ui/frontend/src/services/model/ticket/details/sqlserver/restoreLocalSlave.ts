import type { DetailBase, DetailClusters } from '../common';

export interface RestoreLocalSlave extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    slave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port: number;
    };
  }[];
}
