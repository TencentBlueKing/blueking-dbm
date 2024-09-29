import type { DetailBase, SpecInfo } from '../common';

export interface Apply extends DetailBase {
  group_name: string;
  bk_cloud_id: string;
  ip_source: string;
  db_app_abbr: string;
  city_code: string;
  db_version: string;
  port: number;
  group_id: string;
  disaster_tolerance_level: string;
  nodes: {
    influxdb: [];
  };
  resource_spec: {
    influxdb: SpecInfo;
  };
}
