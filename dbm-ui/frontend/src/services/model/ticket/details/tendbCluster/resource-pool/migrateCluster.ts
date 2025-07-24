import type { BackupSourceType } from '@services/types';

import type { DetailMachines, ResourcePoolDetailBase } from '../../common';

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
  backup_source: BackupSourceType;
  infos: {
    cluster_id: number;
    old_nodes: {
      old_master: IHost[];
      old_slave: IHost[];
    };
    resource_spec: {
      backend_group: {
        count: number;
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
  }[];
  is_safe: boolean;
  machine_infos: DetailMachines;
  need_checksum: boolean;
}
