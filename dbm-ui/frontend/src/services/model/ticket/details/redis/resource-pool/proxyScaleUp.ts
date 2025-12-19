import type { ResourcePoolDetailBase } from '../../resource-pool';

export interface ProxyScaleUp extends ResourcePoolDetailBase {
  infos: {
    bk_cloud_id: number;
    cluster_id: number;
    current_proxy_num: number; // 展示用
    resource_spec: {
      proxy: {
        count: number;
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
    target_proxy_count: number;
  }[];
}
