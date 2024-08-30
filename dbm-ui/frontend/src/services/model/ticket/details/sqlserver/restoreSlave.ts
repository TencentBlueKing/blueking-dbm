import type { DetailBase, DetailClusters } from '../common';

export interface RestoreSlave extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_ids: number[];
    new_slave_host: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port: number;
    };
    old_slave_host: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port: number;
    };
    system_version: string;
  }[];
}
