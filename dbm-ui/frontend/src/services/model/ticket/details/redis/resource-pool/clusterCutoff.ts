import type { InstanceInfos } from '@services/types';

import type { ResourcePoolDetailBase } from '../../common';

interface RoleHost {
  bk_host_id: number;
  ip: string;
  spec_id: number;
}

interface ResourceSpec {
  count: number;
  label_names: string[]; // 标签名称列表，单据详情回显用
  labels: string[]; // 标签id列表
  spec_id: number;
}

interface oldNodes {
  bk_host_id: number;
  ip: string;
  spec: InstanceInfos['spec_config'];
}

export interface ClusterCutoff extends ResourcePoolDetailBase {
  infos: {
    bk_cloud_id: number;
    cluster_ids: number[];
    old_nodes: {
      proxy?: oldNodes[];
      redis_master?: oldNodes[]; // 如果是master则需要拿到主对应的从一起放到old_nodes中
      redis_slave?: oldNodes[];
    };
    proxy?: RoleHost[];
    redis_master?: RoleHost[];
    redis_slave?: RoleHost[];
    resource_spec: {
      [key: `redis_slave_${string}`]: ResourceSpec;
      backend_group?: ResourceSpec; // 如果是master ，这里是backend_group
      new_proxy?: ResourceSpec;
    };
    switch_role: string; // proxy | redis_master | redis_slave
  }[];
}
