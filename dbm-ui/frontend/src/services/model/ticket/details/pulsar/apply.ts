import type { DetailBase, SpecInfo } from '../common';

export interface Apply extends DetailBase {
  ack_quorum: number;
  cluster_alias: string;
  cluster_name: string;
  city_code: string;
  db_app_abbr: string;
  db_version: string;
  disaster_tolerance_level: string;
  ip_source: string;
  nodes: {
    zookeeper: [];
    broker: [];
    bookkeeper: [];
  };
  password: string;
  partition_num: number;
  port: number;
  retention_hours: number;
  replication_num: number;
  resource_spec: {
    zookeeper: SpecInfo;
    broker: SpecInfo;
    bookkeeper: SpecInfo;
  };
  username: string;
}
