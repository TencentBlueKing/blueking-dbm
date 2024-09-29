import type { DetailBase, SpecInfo } from '../common';

export interface InsApply extends DetailBase {
  bk_cloud_id: number;
  cluster_type: string;
  disaster_tolerance_level: string;
  append_apply: boolean; // 是否是追加部署
  port?: number; // 追加就非必填
  city_code?: string; // 追加就非必填
  db_version?: string; // 追加就非必填
  infos: {
    databases: number;
    cluster_name: string;
    // 如果是追加部署，则一定有backend_group，表示追加的主机信息
    backend_group?: {
      master: {
        ip: string;
        bk_cloud_id: number;
        bk_host_id: number;
      };
      slave: {
        ip: string;
        bk_cloud_id: number;
        bk_host_id: number;
      };
    };
  }[];
  // 如果是新部署，则一定从资源池部署
  resource_spec: {
    backend_group: SpecInfo;
  };
}
