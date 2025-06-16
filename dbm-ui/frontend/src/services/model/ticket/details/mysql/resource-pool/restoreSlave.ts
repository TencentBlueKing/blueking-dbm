import type { BackupSourceType, SourceType } from '@services/types';

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
      }[];
    };
    resource_spec: {
      new_slave: {
        hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
  }[];
  source_type: SourceType;
}
