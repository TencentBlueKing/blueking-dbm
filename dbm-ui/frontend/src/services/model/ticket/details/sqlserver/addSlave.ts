import type { DetailBase, DetailClusters } from '../common';

export interface AddSlave extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    new_slave_host: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
  }[];
}
