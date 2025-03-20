import type { DetailBase, SpecInfo } from '../common';

export interface Apply extends DetailBase {
  ack_quorum: number;
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
  resource_spec: {
    bookkeeper: SpecInfo;
    broker: SpecInfo;
    zookeeper: SpecInfo;
  };
  retention_hours: number;
  username: string;
}
