import type { DetailBase } from '../common';

/**
 * TenDB Cluster 数据校验修复
 */

export interface ExcelAuthorizeRules extends DetailBase {
  authorize_data: {
    access_dbs: string[];
    cluster_ids?: number[];
    cluster_type: string;
    source_ips?: {
      bk_host_id?: number;
      ip: string;
    }[];
    target_instances: string[];
    user: string;
  };
  authorize_plugin_infos: {
    access_dbs: string[];
    bk_biz_id: number;
    cluster_ids?: number[];
    cluster_type: string;
    source_ips?: {
      bk_host_id?: number;
      ip: string;
    }[];
    target_instances: string[];
    user: string;
  }[];
  authorize_uid: string;
  excel_url: string;
}
