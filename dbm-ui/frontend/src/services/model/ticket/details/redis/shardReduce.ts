import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface ShardReduce extends DetailBase {
  clusters: DetailClusters;
  infos: {
    bk_cloud_id: number;
    capacity: number;
    cluster_id: number;
    current_group_num: number; // 展示用
    db_version: string;
    future_capacity: number;
    group_num: number; // 新机器组数
    shard_num: number; // 新集群分片数
    spec_id: number; // 展示用
    update_mode: 'slot_migrate_down';
  }[];
  specs: DetailSpecs;
}
