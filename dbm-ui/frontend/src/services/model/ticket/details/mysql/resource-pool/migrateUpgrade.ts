import type { ResourcePoolDetailBase } from '../../common';

export interface MigrateUpgrade extends ResourcePoolDetailBase {
  backup_source: 'local' | 'remote';
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
    pkg_id: number;
    read_only_slaves: {
      new_slave: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      };
      old_slave: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      };
    }[];
    resource_spec: {
      new_master: {
        hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
        spec_id: number;
      };
      new_slave: {
        hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
        spec_id: number;
      };
    };
  }[];
}
