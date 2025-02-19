import type { DetailBase, SpecInfo } from '../common';

export interface Apply extends DetailBase {
  bk_cloud_id: string;
  city_code: string;
  db_app_abbr: string;
  db_version: string;
  disaster_tolerance_level: string;
  group_id: string;
  group_name: string;
  ip_source: string;
  nodes: {
    influxdb: [];
  };
  port: number;
  resource_spec: {
    influxdb: SpecInfo;
  };
}
