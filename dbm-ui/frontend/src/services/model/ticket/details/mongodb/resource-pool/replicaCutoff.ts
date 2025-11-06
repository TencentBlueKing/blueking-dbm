import type { ClusterTypes } from '@common/const';

import type { DetailSpecs, ResourcePoolDetailBase } from '../../common';

interface RoleInfo {
  bk_cloud_id: number;
  bk_host_id: number;
  down: boolean;
  ip: string;
  spec: Pick<DetailSpecs[string], 'cpu' | 'device_class' | 'id' | 'mem' | 'name' | 'qps' | 'storage_spec'>;
}

export interface ReplicaCutoff extends ResourcePoolDetailBase {
  cluster_type: ClusterTypes.MONGO_REPLICA_SET;
  infos: {
    cluster_id: number;
    mongo_config: RoleInfo[];
    mongodb: RoleInfo[];
    mongos: RoleInfo[];
    old_nodes: {
      mongodb: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
    };
    resource_spec: {
      new_mongodb: {
        count: number;
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
    switch_role: string;
  }[];
}
