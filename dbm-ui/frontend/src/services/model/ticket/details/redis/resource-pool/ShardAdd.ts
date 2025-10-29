import type { ResourcePoolDetailBase } from '../../common';

export interface ShardAdd extends ResourcePoolDetailBase {
  infos: {
    bk_cloud_id: number;
    capacity: number;
    cluster_id: number;
    db_version: string;
    future_capacity: number;
    group_num: number; // 新机器组数
    resource_spec: {
      backend_group: {
        count: number; // 申请的机器组数
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
    shard_num: number; // 新集群分片数
    update_mode: 'slot_migrate_up';
  }[];
}
