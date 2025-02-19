import type { ResourcePoolDetailBase } from '../../common';

export interface RestoreSlave extends ResourcePoolDetailBase {
  infos: {
    bk_cloud_id: number;
    cluster_ids: number[];
    old_nodes: {
      old_slave_host: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
    };
    resource_params: {
      os_type: string;
    };
    resource_spec: {
      sqlserver_ha: {
        affinity: string;
        hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
        location_spec: {
          city: string;
          sub_zone_ids: number[];
        };
        spec_id: number;
      };
    };
    system_version: string[];
  }[];
}
