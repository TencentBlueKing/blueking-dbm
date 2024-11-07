import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

// redis 集群迁移
export interface MigrateCluster extends DetailBase {
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
      instance: string;
      db_version: string[];
    };
  }[];
}
