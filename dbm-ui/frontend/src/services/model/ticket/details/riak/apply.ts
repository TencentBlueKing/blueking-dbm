import type { ApplySpecInfo, DetailBase } from '../common';

export interface Apply extends DetailBase {
  bk_cloud_id: number;
  bk_cloud_name: string;
  /** 新协议：地域标识（随机时 default）；存量单据用 city_code */
  bk_cloud_region?: string;
  city_code: string;
  city_name: string;
  cluster_alias: string;
  cluster_name: string;
  db_app_abbr: string;
  db_module_id: number;
  db_module_name: string;
  db_version: string;
  disaster_tolerance_level: string;
  ip_source: string;
  nodes?: {
    riak: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
  };
  resource_spec?: {
    riak: ApplySpecInfo;
  };
}
