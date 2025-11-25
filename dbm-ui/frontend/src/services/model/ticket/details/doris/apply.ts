import type { HostInfo } from '@services/types';

import type { ApplySpecInfo, DetailBase } from '../common';

export interface Apply extends DetailBase {
  bk_cloud_id: number;
  bk_cloud_name: string;
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
}
