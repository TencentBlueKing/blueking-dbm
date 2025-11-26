import type { BackupSourceType } from '@services/types';

import type { ResourcePoolDetailBase } from '../../common';

/**
 * MySQL 单节点迁移
 */

export interface MigrateSingle extends ResourcePoolDetailBase {
  migrate_type: 'instance' | 'machine' | 'failover';
  backup_source: BackupSourceType;
  infos: {
    cluster_ids: number[];
    old_orphan: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
    resource_spec: {
      bk_new_orphan: {
        spec_id: number;
        labels: string[];
        label_names: string[];
        count: number;
      };
    };
    related_cluster_infos: {
      cluster_id: number;
      instance_address: string;
      master_domain: string;
    }[];
  }[];
  ip_source: 'resource_pool';
  orphan_restore_type: string;
}
