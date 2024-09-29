import type { DetailBase } from '../common';

/**
 * MySQL授权
 */
export interface AuthorizeRules extends DetailBase {
  authorize_uid: string;
  authorize_data: {
    access_dbs: string[];
    cluster_type: string;
    cluster_ids: number[];
    source_ips: {
      bk_host_id?: number;
      ip: string;
    }[];
    target_instances: string[];
    user: string;
    privileges?: {
      priv: string;
      user: string;
      access_db: string;
    }[];
  };
  // 导入授权
  excel_url: string;
  authorize_data_list: {
    access_dbs: string[];
    cluster_type: string;
    cluster_ids: number[];
    source_ips: string[];
    target_instances: string[];
    user: string;
  }[];
  // 插件授权
  authorize_plugin_infos: {
    access_dbs: string[];
    bk_biz_id: number;
    cluster_type: string;
    cluster_ids: number[];
    source_ips: string[];
    target_instances: string[];
    user: string;
  }[];
}
