import type { HostInfo } from '@services/types';

import type { ApplySpecInfo, DetailBase } from '../common';

export interface Apply extends DetailBase {
  apply_clb?: boolean;
  apply_polaris?: boolean;
  bk_cloud_id: number;
  bk_cloud_name: string;
  /** 新协议：地域标识（随机时 default）；存量单据用 city_code */
  bk_cloud_region?: string;
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
    client?: ApplySpecInfo;
    cold?: ApplySpecInfo;
    hot?: ApplySpecInfo;
    master: ApplySpecInfo;
  };
}
