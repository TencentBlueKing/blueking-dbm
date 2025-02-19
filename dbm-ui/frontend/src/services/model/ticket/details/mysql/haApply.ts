import type { DetailBase, SpecInfo } from '../common';

export interface HaApply extends DetailBase {
  bk_cloud_id: number;
  charset: string;
  city_code: string;
  city_name: string;
  cluster_count: number;
  db_module_id: number;
  db_module_name: string;
  db_version: string;
  disaster_tolerance_level: string;
  domains: {
    key: string;
    master: string;
    slave: string;
  }[];
  inst_num: number;
  ip_source: string;
  nodes?: {
    backend: { bk_cloud_id: number; bk_host_id: number; ip: string }[];
    proxy: { bk_cloud_id: number; bk_host_id: number; ip: string }[];
  };
  resource_spec?: {
    backend: SpecInfo;
    backend_group: SpecInfo;
    proxy: SpecInfo;
  };
  spec: string;
  spec_display: string;
  start_mysql_port: number;
  start_proxy_port: number;
}
