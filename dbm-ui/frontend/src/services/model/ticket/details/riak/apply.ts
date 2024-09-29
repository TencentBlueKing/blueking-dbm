import type { DetailBase, SpecInfo } from '../common';

export interface Apply extends DetailBase {
  db_module_name: string;
  cluster_name: string;
  cluster_alias: string;
  bk_cloud_name: string;
  city_code: string;
  city_name: string;
  db_version: string;
  ip_source: string;
  resource_spec: {
    riak: SpecInfo;
  };
  nodes?: {
    riak: {
      ip: string;
      bk_host_id: number;
      bk_cloud_id: number;
    }[];
  };
}
