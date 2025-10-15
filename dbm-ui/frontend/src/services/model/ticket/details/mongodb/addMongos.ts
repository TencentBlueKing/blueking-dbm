import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface AddMongos extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    current_mongos_num: number; // 展示用
    resource_spec: {
      mongos: {
        count: number;
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
    role: string;
  }[];
  ip_source: string;
  is_safe: boolean;
  specs: DetailSpecs;
}
