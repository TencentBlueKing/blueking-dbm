import { BackupSourceType, SourceType } from '@services/types';

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
        label_values: string[]; // 标签value列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
  }[];
  source_type: SourceType;
}
