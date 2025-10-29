import type { DetailSpecs, ResourcePoolDetailBase } from '../../common';

interface RoleInfo {
  bk_cloud_id: number;
  bk_host_id: number;
  down: boolean;
  ip: string;
  spec: Pick<DetailSpecs[string], 'cpu' | 'device_class' | 'id' | 'mem' | 'name' | 'qps' | 'storage_spec'>;
}

interface oldNode {
  bk_cloud_id: number;
  bk_host_id: number;
  ip: string;
}

interface ResourceSpec {
  count: number;
  label_names: string[]; // 标签名称列表，单据详情回显用
  labels: string[]; // 标签id列表
  spec_id: number;
}

export interface ShardCutoff extends ResourcePoolDetailBase {
  infos: {
    cluster_id: number;
    mongo_config: RoleInfo[];
    mongodb: RoleInfo[];
    mongos: RoleInfo[];
    old_nodes: {
      mongo_config?: oldNode[];
      mongodb?: oldNode[];
      mongos?: oldNode[];
    };
    resource_spec: {
      new_mongo_config?: ResourceSpec;
      new_mongodb?: ResourceSpec;
      new_mongos?: ResourceSpec;
    };
    switch_role: string;
  }[];
}
