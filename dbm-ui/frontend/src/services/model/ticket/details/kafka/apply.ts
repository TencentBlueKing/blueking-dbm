import type { HostInfo } from '@services/types';

import type { ApplySpecInfo, DetailBase, DetailSpecs } from '../common';

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
  no_security?: number;
  nodes: {
    client: HostInfo[];
    cold: HostInfo[];
    hot: HostInfo[];
    master: HostInfo[];
  };
  partition_num: number;
  port: number;
  replication_num: number;
  resource_spec: {
    broker: ApplySpecInfo;
    zookeeper: ApplySpecInfo;
  };
  retention_bytes: number;
  retention_hours: number;
  specs: DetailSpecs;
}
