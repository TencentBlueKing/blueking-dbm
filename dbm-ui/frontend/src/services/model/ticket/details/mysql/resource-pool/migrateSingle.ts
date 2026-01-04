import type { BackupSourceType } from '@services/types';

import type { ResourcePoolDetailBase } from '../../resource-pool';

/**
 * MySQL 单节点迁移
 */

export interface MigrateSingle extends ResourcePoolDetailBase {
  backup_source: BackupSourceType;
  infos: {
    cluster_ids: number[];
    old_orphan: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
    related_cluster_infos: {
      cluster_id: number;
      instance_address: string;
      master_domain: string;
    }[];
    resource_spec: {
      bk_new_orphan: {
        count: number;
        label_names: string[];
        labels: string[];
        spec_id: number;
      };
    };
  }[];
  ip_source: 'resource_pool';
  migrate_type: 'instance' | 'machine' | 'failover';
  orphan_restore_type: string;
}
