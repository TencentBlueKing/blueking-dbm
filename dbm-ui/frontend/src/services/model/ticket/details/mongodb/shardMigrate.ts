import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface ShardMigrate extends DetailBase {
  clusters: DetailClusters;
  infos: {
    city_code: string;
    cluster_id: number;
    current_shard_nodes_num: number; // 当前每分片节点数
    db_version: string;
    disaster_tolerance_level: string;
    old_nodes: {
      shard: [
        {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        },
      ];
    };
    related_instances: {
      domain: string;
      instances: string[];
    }[]; // 展示用
    resource_spec: {
      mongodb_: {
        count: number;
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
    shard_name: string[];
  }[];
  ip_source: 'resource_pool';
  specs: DetailSpecs;
}
