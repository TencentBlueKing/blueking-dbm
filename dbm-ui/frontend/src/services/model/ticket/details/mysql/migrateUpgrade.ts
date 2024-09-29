import type { DetailBase, DetailClusters } from '../common';

export interface MigrateUpgrade extends DetailBase {
  backup_source: 'local' | 'remote';
  clusters: DetailClusters;
  force: boolean;
  infos: {
    cluster_ids: number[];
    display_info: {
      charset: string;
      current_module_name: string;
      current_package: string;
      current_version: string;
      old_master_slave: string[];
      target_module_name: string;
      target_package: string;
      target_version: string;
    };
    new_db_module_id: number;
    new_master: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
    new_slave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
    pkg_id: number;
    read_only_slaves: {
      old_slave: {
        bk_biz_id: number;
        bk_host_id: number;
        ip: string;
        bk_cloud_id: number;
      };
      new_slave: {
        bk_biz_id: number;
        bk_host_id: number;
        ip: string;
        bk_cloud_id: number;
      };
    }[];
    resource_spec: {
      backend_group: {
        affinity: string;
        count: number;
        location_spec: {
          city: string;
          sub_zone_ids: number[];
        };
        spec_id: number;
      };
    };
  }[];
  ip_source: string;
}
