import type { DetailBase, SpecInfo } from '../common';

export interface ReplicasetApply extends DetailBase {
  bk_cloud_name: string;
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
  node_count: number;
  node_replica_count: number;
  oplog_percent: number;
  proxy_port: number;
  replica_count: number;
  replica_sets: Array<{
    domain: string;
    name: string;
    set_id: string;
  }>;
  resource_spec: {
    mongo_machine_set: SpecInfo;
  };
  start_port: number;
}
