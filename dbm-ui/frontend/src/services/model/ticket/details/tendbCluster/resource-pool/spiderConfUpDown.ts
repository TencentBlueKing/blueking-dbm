import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

import type { ResourcePoolDetailBase } from '../../resource-pool';

/**
 *  TenDB Cluster 接入层升降配
 */

export interface SpiderConfUpDown extends ResourcePoolDetailBase {
  infos: {
    cluster_id: number;
    old_nodes: {
      [x in string]: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
    };
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
      spec: TendbClusterModel['spider_master'][0]['spec_config'];
    }[];
    switch_spider_role: string;
  }[];
  ip_source: 'resource_pool';
  is_safe: boolean;
}
