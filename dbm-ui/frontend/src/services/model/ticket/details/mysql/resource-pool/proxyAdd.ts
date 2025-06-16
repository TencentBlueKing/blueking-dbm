import { SourceType } from '@services/types';

import type { ResourcePoolDetailBase } from '../../common';

export interface ProxyAdd extends ResourcePoolDetailBase {
  infos: {
    cluster_ids: number[];
    resource_spec: {
      new_proxy: {
        hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
          port: number;
        }[];
        label_values: string[]; // 标签value列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
  }[];
  source_type: SourceType;
}
