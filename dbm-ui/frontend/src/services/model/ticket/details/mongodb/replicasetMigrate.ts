import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface ReplicasetMigrate extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_ids: number[];
    current_replicaset_nodes_num: number; // 当前一个副本集的节点数量
    db_version: string;
    disaster_tolerance_level: string;
    old_nodes: {
      replicaset: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
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
  }[];
  ip_source: 'resource_pool';
  specs: DetailSpecs;
}
