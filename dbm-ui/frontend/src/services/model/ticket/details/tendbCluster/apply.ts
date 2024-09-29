import type { DetailBase, SpecInfo } from '../common';

export interface Apply extends DetailBase {
  bk_cloud_id: number;
  db_app_abbr: string;
  cluster_name: string;
  cluster_alias: string;
  ip_source: string;
  city_code: string;
  db_module_id: number;
  spider_port: number;
  cluster_shard_num: number;
  remote_shard_num: number;
  bk_cloud_name: string;
  charset: string;
  version: {
    db_version: string;
    spider_version: string;
  };
  db_module_name: string;
  city_name: string;
  machine_pair_cnt: number;
  disaster_tolerance_level: string;
  resource_spec: {
    spider: SpecInfo;
    backend_group: {
      count: number;
      spec_id: number;
      spec_info: SpecInfo;
      capacity: string;
      future_capacity: string;
    };
  };
}
