import type { ResourcePoolDetailBase } from '../../common';

export interface ProxyAdd extends ResourcePoolDetailBase {
  infos: {
    cluster_ids: number[];
    current_proxy_num?: number;
    resource_spec: {
      new_proxys: {
        count: number;
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
  }[];
}
