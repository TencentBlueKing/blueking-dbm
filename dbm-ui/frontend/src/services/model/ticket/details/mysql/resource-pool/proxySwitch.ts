import type { OperaObejctType } from '@services/types';

import type { ResourcePoolDetailBase } from '../../common';

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
        hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
          port: number;
        }[];
      };
    };
  }[];
  opera_object: OperaObejctType.INSTANCE | OperaObejctType.MACHINE;
}
