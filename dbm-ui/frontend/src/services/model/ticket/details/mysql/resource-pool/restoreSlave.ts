import type { BackupSourceType } from '@services/types';

import type { ResourcePoolDetailBase } from '../../common';

/**
 * MySQL Slave重建
 */
export interface RestoreSlave extends ResourcePoolDetailBase {
  backup_source: BackupSourceType;
  infos: {
    cluster_ids: number[];
    old_nodes: {
      old_slave: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port?: number;
      }[];
    };
    resource_spec: {
      new_slave: {
        hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
          port?: number;
        }[];
        spec_id: number;
      };
    };
  }[];
}
