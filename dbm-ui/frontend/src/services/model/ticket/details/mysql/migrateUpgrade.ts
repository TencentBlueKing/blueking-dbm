import type { DetailBase, DetailClusters } from '../common';

export interface MigrateUpgrade extends DetailBase {
  backup_source: 'local' | 'remote';
  clusters: DetailClusters;
  force: boolean;
  infos: {
    cluster_ids: number[];
    new_db_module_id: number;
    pkg_id: string;
    new_master: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port?: number;
    };
    new_slave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port?: number;
    };
    display_info: {
      current_version: string;
      target_version: string;
      current_package: string;
      target_package: string;
      charset: string;
      current_module_name: string;
      target_module_name: string;
      old_master_slave: string[];
    };
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
  }[];
  ip_source: string;
  nodes: Record<
    string,
    {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_cpu: number;
      bk_disk: number;
      bk_host_id: number;
      bk_mem: number;
      city: string;
      device_class: string;
      ip: string;
      rack_id: string;
      storage_device: Record<
        string,
        {
          disk_id: string;
          disk_type: string;
          file_type: string;
          size: number;
        }
      >;
      sub_zone: string;
      sub_zone_id: string;
    }
  >;
}
