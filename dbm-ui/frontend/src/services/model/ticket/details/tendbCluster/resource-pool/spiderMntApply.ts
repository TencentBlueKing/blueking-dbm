import type { ResourcePoolDetailBase } from '../../common';

/**
 *  TenDB Cluster 添加运维节点
 */

export interface SpiderMntApply extends ResourcePoolDetailBase {
  infos: {
    bk_cloud_id: string;
    cluster_id: number;
    resource_spec: {
      spider_ip_list: {
        count: number;
        hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
        spec_id: number;
      };
    };
  }[];
  ip_source: 'resource_pool';
}
