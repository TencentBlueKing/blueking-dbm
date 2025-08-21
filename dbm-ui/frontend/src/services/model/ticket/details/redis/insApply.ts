import type { DetailBase, SpecInfo } from '../common';

export interface InsApply extends DetailBase {
  append_apply: boolean; // 是否是追加部署
  bk_cloud_id: number;
  city_code?: string; // 追加就非必填
  cluster_type: string;
  db_version?: string; // 追加就非必填
  disaster_tolerance_level: string;
  infos: {
    // 如果是追加部署，则一定有backend_group，表示追加的主机信息
    backend_group?: {
      master: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      };
      slave: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      };
    };
    cluster_name: string;
    databases: number;
  }[];
  port?: number; // 追加就非必填
  // 如果是新部署，则一定从资源池部署
  resource_spec?: {
    backend_group: SpecInfo;
  };
}
