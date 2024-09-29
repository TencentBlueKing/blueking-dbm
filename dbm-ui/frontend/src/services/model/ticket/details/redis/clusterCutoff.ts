import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface ClusterCutoff extends DetailBase {
  clusters: DetailClusters;
  infos: {
    bk_cloud_id: number;
    cluster_id?: number; // 旧协议，兼容旧单据用
    cluster_ids: number[];
    display_info: {
      data: {
        ip: string;
        role: string;
        spec_id: number;
        spec_name: string;
      }[];
    };
    proxy: {
      ip: string;
      spec_id: number;
    }[];
    redis_master: {
      ip: string;
      spec_id: number;
    }[];
    redis_slave: {
      ip: string;
      spec_id: number;
    }[];
    resource_spec: {
      backend_group: {
        affinity: string;
        count: number;
        location_spec: {
          city: string;
          sub_zone_ids: number[];
        };
        spec_id: number;
      };
    };
  }[];
  ip_source: 'resource_pool';
  specs: DetailSpecs;
}
