import type { DetailBase, DetailClusters } from '../common';

export interface SpiderUpgrade extends DetailBase {
  clusters: DetailClusters;
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
        labels?: string[];
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
  is_safe: boolean;
}
