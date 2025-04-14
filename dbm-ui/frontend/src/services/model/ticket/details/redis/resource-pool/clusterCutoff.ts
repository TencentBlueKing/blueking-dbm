import type { ResourcePoolDetailBase } from '../../common';

type RoleHostItem = {
  bk_host_id: number;
  ip: string;
  master_ip: string;
  master_spec_id: number;
  spec_id: number;
}[];

interface RoleHost {
  proxy: RoleHostItem;
  redis_master: RoleHostItem;
  redis_slave: RoleHostItem;
}

export interface ClusterCutoff extends ResourcePoolDetailBase {
  infos: {
    bk_cloud_id: number;
    cluster_ids: number[];
    old_nodes: RoleHost;
    proxy: RoleHostItem;
    redis_master: RoleHostItem;
    redis_slave: RoleHostItem;
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
