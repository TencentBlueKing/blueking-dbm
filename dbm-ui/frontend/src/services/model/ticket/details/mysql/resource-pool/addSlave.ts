import { BackupSourceType } from '@services/types';

import type { ResourcePoolDetailBase } from '../../common';

/**
 * MySQL 添加从库
 */

export interface AddSlave extends ResourcePoolDetailBase {
  backup_source: BackupSourceType;
  infos: {
    cluster_ids: number[];
    resource_spec: {
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
