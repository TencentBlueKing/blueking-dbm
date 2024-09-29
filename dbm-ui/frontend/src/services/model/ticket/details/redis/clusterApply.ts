import type { HostInfo } from '@services/types';

import type { ClusterTypes } from '@common/const';

import type { DetailBase, SpecInfo } from '../common';

export interface ClusterApply extends DetailBase {
  bk_cloud_id: number;
  cap_key: string;
  city_code: string;
  city_name: string;
  cluster_alias: string;
  cluster_name: string;
  cluster_type: ClusterTypes;
  cap_spec: string;
  db_version: string;
  db_app_abbr: string;
  disaster_tolerance_level: string;
  ip_source: string;
  nodes: {
    proxy: HostInfo[];
    master: HostInfo[];
    slave: HostInfo[];
  };
  proxy_port: number;
  proxy_pwd: string;
  resource_spec: {
    proxy: SpecInfo;
    backend_group: {
      affinity: string;
      count: number;
      spec_id: number;
      spec_info: {
        spec_name: string;
        machine_pair: number;
        cluster_shard_num: number;
        cluster_capacity: number;
        qps: {
          max: number;
          min: number;
        };
      };
      location_spec: {
        city: string;
        sub_zone_ids: number[];
      };
    };
  };
}
