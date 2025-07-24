import type { BackupSourceType } from '@services/types';

import type { DetailMachines, ResourcePoolDetailBase } from '../../common';

/**
 * TenDB Cluster Slave重建
 */
export interface RestoreSlave extends ResourcePoolDetailBase {
  backup_source: BackupSourceType;
  infos: {
    cluster_id: number;
    old_nodes: {
      old_slave: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
    };
    resource_spec: {
      new_slave: {
        count: number;
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
  }[];
  machine_infos: DetailMachines;
}
