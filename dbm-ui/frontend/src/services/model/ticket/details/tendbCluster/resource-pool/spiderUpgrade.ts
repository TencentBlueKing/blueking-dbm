import type { ResourcePoolDetailBase } from '../../resource-pool';

export interface SpiderUpgrade extends ResourcePoolDetailBase {
  infos: {
    cluster_id: number;
    current_version: {
      charset: string;
      db_module_name: string;
      db_version: string;
      pkg_name: string;
    };
    new_db_module_id: number;
    old_nodes: {
      spider_master: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
      spider_slave: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
    };
    pkg_id: number;
    resource_spec: {
      [key in string]: {
        count: number;
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
    target_version: {
      charset: string;
      db_module_name: string;
      db_version: string;
      pkg_name: string;
    };
  }[];
  ip_source: 'resource_pool';
  is_check_process: boolean;
  upgrade_local: boolean;
}
