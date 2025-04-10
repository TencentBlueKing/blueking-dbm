import type { OperaObejctType } from '@services/types';

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
      new_master: {
        hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
          port: number;
        }[];
        spec_id: number;
      };
      new_slave: {
        hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
          port: number;
        }[];
        spec_id: number;
      };
    };
  }[];
  is_safe: boolean;
  machine_infos: DetailMachines;
  opera_object: OperaObejctType.CLUSTER | OperaObejctType.MACHINE;
}
