import type { ResourcePoolDetailBase } from '../../resource-pool';

export interface ScaleUpdown extends ResourcePoolDetailBase {
  infos: {
    cluster_id: number;
    cluster_type: string;
    db_version: string;
    disaster_tolerance_level: string;
    old_nodes: {
      mongodb: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
    };
    resource_spec: {
      mongodb: {
        count: number;
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
    shard_machine_group: number;
    shard_node_count: number;
    shards_num: number;
  }[];
}
