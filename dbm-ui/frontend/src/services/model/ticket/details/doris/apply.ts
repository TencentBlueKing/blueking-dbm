import type { HostInfo } from '@services/types';

import type { DetailBase, SpecInfo } from '../common';

export interface Apply extends DetailBase {
  city_code: string;
  cluster_alias: string;
  cluster_name: string;
  db_app_abbr: string;
  db_version: string;
  disaster_tolerance_level: string;
  http_port: number;
  ip_source: string;
  nodes?: {
    cold: HostInfo[];
    follower: HostInfo[];
    hot: HostInfo[];
    observer: HostInfo[];
  };
  query_port: number;
  resource_spec?: {
    cold: SpecInfo;
    follower: SpecInfo;
    hot: SpecInfo;
    observer: SpecInfo;
  };
}
