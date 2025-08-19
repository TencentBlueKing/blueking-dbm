import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

// redis 集群迁移
export interface MigrateCluster extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    db_version: string[];
    // 历史协议
    display_info?: {
      db_version: string[];
      instance: string;
    };
    migrate_instance: string;
    old_nodes?: MigrateCluster['infos'][number]['origin_old_nodes']; // 历史协议
    origin_old_nodes: {
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
