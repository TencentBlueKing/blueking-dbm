import type { ResourcePoolDetailBase } from '../../common';

export interface ScaleOut extends ResourcePoolDetailBase {
  cluster_id: number;
  resource_spec: {
    riak: {
      count: number;
      hosts: {
        agent_status: string;
        bk_cloud_id: number;
        bk_disk: string;
        bk_host_id: number;
        ip: string;
      }[];
      spec_id: number;
    };
  };
}
