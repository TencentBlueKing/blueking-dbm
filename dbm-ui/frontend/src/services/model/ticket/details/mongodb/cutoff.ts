import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface Cutoff extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    mongo_config: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      spec_id: number;
    }[];
    mongodb: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      spec_id: number;
    }[];
    mongos: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      spec_id: number;
    }[];
    resource_spec: {
      [k in string]: {
        count: number;
        location_spec: {
          city: string;
          sub_zone_ids: number[];
        };
        spec_id: number;
      };
    };
  }[];
  ip_source: string;
  specs: DetailSpecs;
}
