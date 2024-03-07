import type { DetailBase, DetailClusters } from '../common';

export interface MasterFailOver extends DetailBase {
  clusters: DetailClusters;
  force: boolean;
  infos: {
    cluster_ids: number[];
    master: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
    slave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
  }[];
}
