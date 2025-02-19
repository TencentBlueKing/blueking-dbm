import type { ResourcePoolDetailBase } from '../../common';
/**
 * TenDB Cluster 主从迁移
 */

interface IHost {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_host_id: number;
  ip: string;
}

export interface MigrateCluster extends ResourcePoolDetailBase {
  backup_source: string;
  infos: {
    cluster_id: number;
    old_nodes: {
      old_master: IHost[];
      old_slave: IHost[];
    };
    resource_spec: {
      backend_group: {
        count: number;
        spec_id: number;
      };
    };
  }[];
  is_safe: boolean;
}
