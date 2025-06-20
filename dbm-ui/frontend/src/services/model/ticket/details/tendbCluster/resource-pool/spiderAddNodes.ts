import type { ResourcePoolDetailBase } from '../../common';

/**
 *  TenDB Cluster 扩容接入层
 */

export interface SpiderAddNodes extends ResourcePoolDetailBase {
  infos: {
    add_spider_role: string;
    cluster_id: number;
    resource_spec: {
      spider_ip_list: {
        count: number;
        label_values: string[]; // 标签value列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
  }[];
}
