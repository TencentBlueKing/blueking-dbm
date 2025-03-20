import type { ResourcePoolDetailBase } from '../../common';

export interface ProxyAdd extends ResourcePoolDetailBase {
  infos: {
    cluster_ids: number[];
    resource_spec: {
      new_proxy: {
        hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
          port: number;
        }[];
        spec_id: number;
      };
    };
  }[];
}
