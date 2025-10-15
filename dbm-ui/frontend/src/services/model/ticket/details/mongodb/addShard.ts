import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface AddShard extends DetailBase {
  clusters: DetailClusters;
  infos: {
    add_shards_num: number; // 新增分片数
    city_code: string;
    cluster_id: number;
    current_shard_nodes_num: number; // 当前每分片节点数
    current_shards_num: number; // 展示用
    db_version: string;
    disaster_tolerance_level: string; // 亲和性
    node_replicaset_count: number; // 单机部署实例数
    resource_spec: {
      mongodb: {
        count: number; // 台数
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
    single_host_shard_num: number; // 展示用
  }[];
  ip_source: 'resource_pool';
  specs: DetailSpecs;
}
