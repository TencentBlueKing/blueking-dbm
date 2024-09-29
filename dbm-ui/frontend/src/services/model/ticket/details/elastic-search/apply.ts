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
  nodes: {
    client: HostInfo[];
    master: HostInfo[];
    hot: HostInfo[];
    cold: HostInfo[];
  };
  resource_spec: {
    master: SpecInfo;
    client: SpecInfo;
    hot: SpecInfo;
    cold: SpecInfo;
  };
}
