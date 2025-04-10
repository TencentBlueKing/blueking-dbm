import type { DetailMachines, ResourcePoolDetailBase } from '../../common';

export interface ReduceMongos extends ResourcePoolDetailBase {
  infos: {
    cluster_id: number;
    old_nodes: {
      mongos: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
    };
    reduce_count: number;
    role: string;
  }[];
  mackine_infos: DetailMachines;
}
