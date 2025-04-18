import type { ResourcePoolDetailBase } from '../../common';

export interface ScaleIn extends ResourcePoolDetailBase {
  cluster_id: number;
  old_nodes: {
    riak: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
  };
}
