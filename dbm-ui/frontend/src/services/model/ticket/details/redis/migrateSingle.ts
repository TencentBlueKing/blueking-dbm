import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

// redis 主从迁移
export interface MigrateSingle extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    db_version: string;
    display_info: {
      domain: string;
      ip: string;
      migrate_type: string; // domain | machine
    };
    old_nodes: {
      master: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
      }[];
      slave: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
      }[];
    };
    resource_spec: {
      backend_group: {
        count: number;
        spec_id: number;
      };
    };
  }[];
  specs: DetailSpecs;
}
