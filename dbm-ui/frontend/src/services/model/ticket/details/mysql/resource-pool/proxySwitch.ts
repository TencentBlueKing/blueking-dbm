import type { OperaObejctType } from '@services/types';
import TendbhaModel from '@services/model/mysql/tendbha';
import type { DetailMachines, ResourcePoolDetailBase } from '../../common';

/**
 * MySQL 替换Proxy
 */

export interface ProxySwitch extends ResourcePoolDetailBase {
  force: boolean;
  infos: {
    cluster_ids: number[];
    old_nodes: {
      origin_proxy: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
        spec: TendbhaModel['masters'][number]['spec_config'];
      }[];
    };
    related_instances?: {
      cluster_id: number;
      instance_address: string;
    }[];
    origin_proxy_ip: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      spec: TendbhaModel['masters'][number]['spec_config'];
    };
    resource_spec: {
      target_proxy: {
        count: number;
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
  }[];
  machine_infos: DetailMachines;
  opera_object: OperaObejctType.INSTANCE | OperaObejctType.MACHINE;
}
