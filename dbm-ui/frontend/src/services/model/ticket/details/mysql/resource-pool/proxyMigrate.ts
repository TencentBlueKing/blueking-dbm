import type { ResourcePoolDetailBase } from '../../common';
import TendbhaModel from '@services/model/mysql/tendbha';

export interface ProxyMigrate extends ResourcePoolDetailBase {
  infos: {
    cluster_ids: number[];
    old_nodes: {
      proxy: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
        spec: TendbhaModel['proxies'][0]['spec_config'];
      }[];
    };
    origin_proxys: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port: number;
      spec: TendbhaModel['masters'][number]['spec_config'];
    }[];
    related_instances?: {
      cluster_id: number;
      instance_address: string;
    }[];
    resource_spec: {
      target_proxys: {
        count: number; // proxy 数量
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
  }[];
}
