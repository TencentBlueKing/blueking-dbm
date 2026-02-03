import type { ResourcePoolDetailBase } from '../../resource-pool';

export interface MigrateUpgrade extends ResourcePoolDetailBase {
  backup_source: 'local' | 'remote';
  infos: {
    cluster_ids: number[];
    display_info: {
      charset: string;
      current_module_name: string;
      current_package: string;
      current_version: string;
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
        bk_sub_zone: string;
        ip: string;
      };
      old_slave: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        bk_sub_zone: string;
        ip: string;
      };
    }[];
    resource_spec: {
      backend_group: {
        count: number;
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
      new_read_slave?: {
        count: number;
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
  }[];
  is_check_process: boolean;
  need_checksum: boolean;
}
