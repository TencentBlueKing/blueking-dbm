import type { DetailBase, SpecInfo } from '../common';

export interface Apply extends DetailBase {
  bk_cloud_id: number;
  bk_cloud_name: string;
  charset: string;
  city_code: string;
  city_name: string;
  cluster_alias: string;
  cluster_name: string;
  cluster_shard_num: number;
  db_app_abbr: string;
  db_module_id: number;
  db_module_name: string;
  disaster_tolerance_level: string;
  ip_source: string;
  machine_pair_cnt: number;
  remote_shard_num: number;
  resource_spec: {
    backend_group: {
      capacity: string;
      count: number;
      future_capacity: string;
      spec_id: number;
      spec_info: SpecInfo;
    };
    spider: SpecInfo;
  };
  spider_port: number;
  version: {
    db_version: string;
    spider_version: string;
  };
}
