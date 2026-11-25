import type { ApplySpecInfo, DetailBase } from '../common';

export interface Apply extends DetailBase {
  ack_quorum: number;
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
  ip_source: string;
  nodes: {
    bookkeeper: [];
    broker: [];
    zookeeper: [];
  };
  partition_num: number;
  password: string;
  port: number;
  replication_num: number;
  resource_spec?: {
    bookkeeper: ApplySpecInfo;
    broker: ApplySpecInfo;
    zookeeper: ApplySpecInfo;
  };
  retention_hours: number;
  // tags: Record<string, string>[];
  username: string;
}
