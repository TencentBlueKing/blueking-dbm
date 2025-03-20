import type { ResourcePoolDetailBase } from '../../common';

type RoleHostItem = {
  bk_host_id: number;
  ip: string;
  spec_id: number;
}[];

interface RoleHost {
  proxy: RoleHostItem;
  redis_master: RoleHostItem;
  redis_slave: RoleHostItem;
}

export interface ClusterCutoff extends ResourcePoolDetailBase, RoleHost {
  infos: {
    bk_cloud_id: number;
    cluster_ids: number[];
    old_nodes: RoleHost;
    resource_spec: {
      [k in string]: {
        affinity: string;
        count: number;
        group_count: number;
        location_spec: {
          city: string;
          sub_zone_ids: number[];
        };
        spec_id: number;
      };
    };
  }[];
}
