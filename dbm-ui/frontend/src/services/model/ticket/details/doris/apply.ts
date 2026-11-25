import type { HostInfo } from '@services/types';

import type { ApplySpecInfo, DetailBase } from '../common';

export interface Apply extends DetailBase {
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
  enable_cold_storage: boolean;
  http_port: number;
  ip_source: string;
  nodes?: {
    cold: HostInfo[]; // 历史协议，替换为warm
    follower: HostInfo[];
    hot: HostInfo[];
    observer: HostInfo[];
    warm: HostInfo[];
  };
  query_port: number;
  resource_spec?: {
    cold?: ApplySpecInfo; // 历史协议，替换为warm
    follower: ApplySpecInfo;
    hot?: ApplySpecInfo;
    observer?: ApplySpecInfo;
    warm?: ApplySpecInfo;
  };
  // tags: Record<string, string>[];
}
