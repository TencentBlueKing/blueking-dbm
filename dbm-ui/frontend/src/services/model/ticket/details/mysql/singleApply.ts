import type { DetailBase, SpecInfo } from '../common';

export interface SingleApply extends DetailBase {
  bk_cloud_id: number;
  city_code: string;
  city_name: string;
  cluster_count: number;
  charset: string;
  db_module_name: string;
  db_module_id: number;
  db_version: string;
  disaster_tolerance_level: string;
  ip_source: string;
  inst_num: number;
  start_mysql_port: number;
  spec_display: string;
  start_proxy_port: number;
  spec: string;
  domains: {
    key: string;
    master: string;
    slave?: string;
  }[];
  nodes: {
    proxy: { ip: string; bk_host_id: number; bk_cloud_id: number }[];
    backend: { ip: string; bk_host_id: number; bk_cloud_id: number }[];
  };
  resource_spec: {
    proxy: SpecInfo;
    backend_group: SpecInfo;
    backend: SpecInfo;
  };
}
