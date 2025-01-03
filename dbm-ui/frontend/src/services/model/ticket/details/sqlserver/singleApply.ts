import { ClusterTypes } from '@common/const';

import type { DetailBase, SpecInfo } from '../common';

export interface SingleApply extends DetailBase {
  bk_cloud_id: number;
  charset: string;
  city_code: string;
  city_name: string;
  cluster_count: number;
  db_module_id: number;
  db_module_name: string;
  db_version: string;
  domains: {
    key: string;
    master: string;
  }[];
  inst_num: number;
  ip_source: string;
  nodes?: {
    [ClusterTypes.SQLSERVER_SINGLE]: {
      ip: string;
      bk_host_id: number;
      bk_cloud_id: number;
      bk_biz_id: number;
    }[];
  };
  resource_spec?: {
    backend_group: SpecInfo;
  };
  spec: string;
  spec_display: string;
  start_mssql_port: number;
}
