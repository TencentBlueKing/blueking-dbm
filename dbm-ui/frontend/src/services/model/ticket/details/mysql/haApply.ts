import type { ApplySpecInfo, DetailBase } from '../common';

export interface HaApply extends DetailBase {
  apply_clb?: boolean;
  bk_cloud_id: number;
  bk_cloud_name: string;
  /** 新协议：地域标识（随机时 default）；存量单据用 city_code */
  bk_cloud_region?: string;
  /** 表单存储字段（可用区名列表），提交前由 useApplyBase 剔除 */
  bk_cloud_zone_list?: string[];
  charset: string;
  city_code: string;
  city_name: string;
  cluster_count: number;
  db_app_abbr: string;
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
  nodes: {
    backend?: { bk_cloud_id: number; bk_host_id: number; ip: string }[];
    backend_group?: {
      master: { bk_cloud_id: number; bk_host_id: number; ip: string };
      slave: { bk_cloud_id: number; bk_host_id: number; ip: string };
    }[];
    proxy?: { bk_cloud_id: number; bk_host_id: number; ip: string }[];
  };
  resource_spec: {
    backend?: ApplySpecInfo;
    backend_group?: ApplySpecInfo;
    proxy?: ApplySpecInfo;
  };
  spec: string;
  spec_display: string;
  start_mysql_port: number;
  start_proxy_port: number;
}
