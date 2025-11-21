import type { ResourcePoolDetailBase } from '../../common';

export interface ClusterMigrate extends ResourcePoolDetailBase {
  infos: {
    cluster_ids: number[];
    resource_spec: {
      [key in 'backend_group' | 'new_hosts']?: {
        // 主从集群传 backend_group、单节点集群传 new_hosts
        count: number;
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
  }[];
  ip_source: 'resource_pool';
}
