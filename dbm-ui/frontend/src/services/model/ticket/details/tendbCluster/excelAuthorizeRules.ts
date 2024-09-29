import type { DetailBase } from '../common';

/**
 * TenDB Cluster 数据校验修复
 */

export interface ExcelAuthorizeRules extends DetailBase {
  authorize_uid: string;
  authorize_data: {
    access_dbs: string[];
    cluster_type: string;
    cluster_ids?: number[];
    source_ips?: {
      bk_host_id?: number;
      ip: string;
    }[];
    target_instances: string[];
    user: string;
  };
  excel_url: string;
  authorize_plugin_infos: {
    access_dbs: string[];
    bk_biz_id: number;
    cluster_type: string;
    cluster_ids?: number[];
    source_ips?: {
      bk_host_id?: number;
      ip: string;
    }[];
    target_instances: string[];
    user: string;
  }[];
}
