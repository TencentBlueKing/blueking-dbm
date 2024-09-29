import type { DetailBase } from '../common';

export interface TemporaryDestroy extends DetailBase {
  clusters: Record<
    number,
    {
      alias: string;
      bk_biz_id: number;
      bk_cloud_id: number;
      cluster_type: string;
      cluster_type_name: string;
      creator: string;
      db_module_id: number;
      disaster_tolerance_level: string;
      id: number;
      immute_domain: string;
      major_version: string;
      name: string;
      phase: string;
      region: string;
      status: string;
      tag: {
        bk_biz_id: number;
        name: string;
        type: string;
      }[];
      time_zone: string;
      updater: string;
    }
  >;
  cluster_ids: number[];
}
