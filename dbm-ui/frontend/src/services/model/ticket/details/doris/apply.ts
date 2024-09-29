import type { HostInfo } from '@services/types';

import type { DetailBase, SpecInfo } from '../common';

export interface Apply extends DetailBase {
  db_app_abbr: string;
  city_code: string;
  cluster_alias: string;
  cluster_name: string;
  db_version: string;
  disaster_tolerance_level: string;
  http_port: number;
  ip_source: string;
  nodes?: {
    follower: HostInfo[];
    observer: HostInfo[];
    hot: HostInfo[];
    cold: HostInfo[];
  };
  query_port: number;
  resource_spec?: {
    follower: SpecInfo;
    observer: SpecInfo;
    hot: SpecInfo;
    cold: SpecInfo;
  };
}
