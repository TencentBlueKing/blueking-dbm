import type { ResourcePoolDetailBase } from '../../common';

/**
 *  TenDB Cluster 替换接入层
 */

export interface SpiderSwitchNodes extends ResourcePoolDetailBase {
  infos: {
    cluster_id: number;
    resource_spec: {
      [x in string]: {
        count: number;
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
    spider_old_ip_list: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port: number;
    }[];
    switch_spider_role: string;
  }[];
  is_safe: boolean;
  old_nodes: {
    spider_master: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
    spider_slave: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
  };
}
