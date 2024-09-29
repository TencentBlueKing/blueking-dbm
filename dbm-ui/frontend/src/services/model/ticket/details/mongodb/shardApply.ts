import type { DetailBase, SpecInfo } from '../common';

export interface ShardApply extends DetailBase {
  bk_cloud_name: string;
  cap_key: string;
  cap_spec: string;
  city_code: string;
  city_name: string;
  cluster_alias: string;
  cluster_id: number;
  cluster_name: string;
  cluster_type: string;
  db_app_abbr: string;
  db_version: string;
  disaster_tolerance_level: string;
  ip_source: string;
  oplog_percent: number;
  proxy_port: number;
  start_port: number;
  resource_spec: {
    mongo_config: SpecInfo;
    mongos: SpecInfo;
    mongodb: SpecInfo;
  };
}
