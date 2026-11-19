import type { ApplySpecInfo, DetailBase } from '../common';

export interface Apply extends DetailBase {
  bk_cloud_id: string;
  /** 新协议：地域标识（随机时 default）；存量单据用 city_code */
  bk_cloud_region?: string;
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
    influxdb: ApplySpecInfo;
  };
}
