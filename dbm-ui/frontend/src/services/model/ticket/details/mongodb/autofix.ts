import type { DetailBase, DetailClusters } from '../common';

/**
 * MongoDB 故障自愈（替换）
 */
export interface Autofix extends DetailBase {
  clusters: DetailClusters;
  infos: {
    bk_biz_id: number;
    bk_cloud_id: number;
    cluster_ids: number[];
    cluster_type: string;
    immute_domain: string;
    mongod_list: {
      ip: string;
      spec_id?: number;
    }[];
    mongos_list: {
      ip: string;
      spec_id?: number;
    }[];
    resource_spec: Record<string, unknown>;
  }[];
  ip_source: string;
}
