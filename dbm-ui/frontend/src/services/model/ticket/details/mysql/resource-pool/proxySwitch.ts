import type { OperaObejctType, SourceType } from '@services/types';

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
      }[];
    };
    resource_spec: {
      target_proxy: {
        count: number;
        hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
          port: number;
        }[];
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
  }[];
  machine_infos: DetailMachines;
  opera_object: OperaObejctType.INSTANCE | OperaObejctType.MACHINE;
  source_type: SourceType;
}
