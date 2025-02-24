import type { HostInfo } from '@services/types';

import type { ClusterTypes } from '@common/const';

import type { DetailBase, SpecInfo } from '../common';

export interface ClusterApply extends DetailBase {
  bk_cloud_id: number;
  cap_key: string;
  cap_spec: string;
  city_code: string;
  city_name: string;
  cluster_alias: string;
  cluster_name: string;
  cluster_type: ClusterTypes;
  db_app_abbr: string;
  db_version: string;
  disaster_tolerance_level: string;
  ip_source: string;
  nodes: {
    master: HostInfo[];
    proxy: HostInfo[];
    slave: HostInfo[];
  };
  proxy_port: number;
  proxy_pwd: string;
  resource_spec: {
    backend_group: {
      affinity: string;
      count: number;
      location_spec: {
        city: string;
        sub_zone_ids: number[];
      };
      spec_id: number;
      spec_info: {
        cluster_capacity: number;
        cluster_shard_num: number;
        machine_pair: number;
        qps: {
          max: number;
          min: number;
        };
        spec_name: string;
      };
    };
    proxy: SpecInfo;
  };
}
