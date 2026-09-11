import type { DetailBase, DetailClusters } from '../common';

/**
 * MongoDB 故障自愈确认（PRE）
 */
export interface AutofixPre extends DetailBase {
  clusters: DetailClusters;
  infos: {
    autofix_core_id: number;
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    cluster_ids: number[];
    cluster_type: string;
    immute_domain: string;
    ip: string;
    ports: number[];
  }[];
}
