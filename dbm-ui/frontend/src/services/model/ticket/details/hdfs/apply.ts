import type { HostInfo } from '@services/types';

import type { DetailBase, SpecInfo } from '../common';

export interface Apply extends DetailBase {
  bk_cloud_id: number;
  bk_cloud_name: string;
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
    cold: HostInfo[];
    hot: HostInfo[];
    master: HostInfo[];
  };
  resource_spec: {
    datanode: SpecInfo;
    namenode: SpecInfo;
    zookeeper: SpecInfo;
  };
}
