import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

// redis 主从迁移
export interface MigrateSingle extends DetailBase {
  clusters: DetailClusters;
  specs: DetailSpecs;
  infos: {
    cluster_id: number;
    resource_spec: {
      backend_group: {
        spec_id: number;
        count: number;
      };
    };
    db_version: string;
    old_nodes: {
      master: {
        bk_host_id: number;
        ip: string;
        port: number;
        bk_cloud_id: number;
        bk_biz_id: number;
      }[];
      slave: {
        bk_host_id: number;
        ip: string;
        port: number;
        bk_cloud_id: number;
        bk_biz_id: number;
      }[];
    };
    display_info: {
      migrate_type: string; // domain | machine
      ip: string;
      domain: string;
    };
  }[];
}
