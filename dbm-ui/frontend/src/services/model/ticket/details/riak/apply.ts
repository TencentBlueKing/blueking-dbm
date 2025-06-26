import type { DetailBase, SpecInfo } from '../common';

export interface Apply extends DetailBase {
  bk_cloud_id: number;
  bk_cloud_name: string;
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
    riak: SpecInfo;
  };
}
