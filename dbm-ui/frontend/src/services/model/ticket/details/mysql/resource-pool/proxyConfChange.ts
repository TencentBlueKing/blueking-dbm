import type { ResourcePoolDetailBase } from '../../common';
import TendbhaModel from '@services/model/mysql/tendbha';

export interface ProxyConfChange extends ResourcePoolDetailBase {
  infos: {
    cluster_ids: number[];
    origin_proxy_ips: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      spec: TendbhaModel['proxies'][0]['spec_config'];
    }[];
    resource_spec: {
      target_proxy: {
        count: number; // proxy 数量
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
  }[];
}
