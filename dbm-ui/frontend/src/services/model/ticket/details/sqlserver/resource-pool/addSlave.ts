import type { ResourcePoolDetailBase } from '../../common';

export interface AddSlave extends ResourcePoolDetailBase {
  infos: {
    cluster_ids: number[];
    resource_spec: {
      new_slave: {
        count: number;
        hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
        spec_id: number;
      };
    };
  }[];
}
