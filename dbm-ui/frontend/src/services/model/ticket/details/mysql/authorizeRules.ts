import type { DetailBase } from '../common';

/**
 * MySQL授权
 */
export interface AuthorizeRules extends DetailBase {
  authorize_data: {
    access_dbs: string[];
    cluster_ids: number[];
    cluster_type: string;
    privileges?: {
      access_db: string;
      priv: string;
      user: string;
    }[];
    source_ips: {
      bk_host_id?: number;
      ip: string;
    }[];
    target_instances: string[];
    user: string;
  };
  authorize_data_list: {
    access_dbs: string[];
    cluster_ids: number[];
    cluster_type: string;
    source_ips: string[];
    target_instances: string[];
    user: string;
  }[];
  // 插件授权
  authorize_plugin_infos: {
    access_dbs: string[];
    bk_biz_id: number;
    cluster_ids: number[];
    cluster_type: string;
    source_ips: string[];
    target_instances: string[];
    user: string;
  }[];
  authorize_uid: string;
  // 导入授权
  excel_url: string;
}
