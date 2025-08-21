import type { OperaObejctType, SourceType } from '@services/types';

import type { DetailMachines, ResourcePoolDetailBase, ResourcePoolRecycleHost } from '../../common';

/**
 * MySQL 迁移主从
 */

export interface MigrateCluster extends ResourcePoolDetailBase {
  backup_source: string;
  infos: {
    cluster_ids: number[];
    old_nodes: {
      old_master: ResourcePoolRecycleHost[];
      old_slave: ResourcePoolRecycleHost[];
    };
    resource_spec: {
      // 自动匹配走backend_group
      backend_group: {
        count: number;
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
      // 手动选择走new_master、new_slave
      new_master: {
        count: number;
        hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
        spec_id: number;
      };
      new_slave: {
        count: number;
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
  is_safe: boolean;
  machine_infos: DetailMachines;
  need_checksum: boolean;
  opera_object: OperaObejctType.CLUSTER | OperaObejctType.MACHINE;
  source_type: SourceType;
}
