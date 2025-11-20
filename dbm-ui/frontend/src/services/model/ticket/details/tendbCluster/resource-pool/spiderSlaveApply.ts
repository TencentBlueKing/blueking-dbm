import type { ResourcePoolDetailBase } from '../../common';

/**
 *  TenDB Cluster 部署只读接入层
 */

export interface SpiderSlaveApply extends ResourcePoolDetailBase {
  infos: {
    cluster_id: number;
    resource_spec: {
      spider_slave_ip_list: {
        count: number;
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
  }[];
}
