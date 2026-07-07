import type { DetailBase } from '../common';

/**
 * Qdrant 集群部署
 */
export interface HaApply extends DetailBase {
  bk_biz_name: string;
  bk_cloud_id: number;
  bk_cloud_region: string;
  city_code: string;
  cluster_alias: string;
  cluster_name: string;
  cluster_type: string;
  component_list: [
    {
      component_name: 'qdrant';
      replicas: number;
      request_cpu: string;
      request_memory: string;
      storage: string;
    },
  ];
  creator: string;
  db_app_abbr: string;
  db_version: string;
  k8s_cluster_name: string;
  major_version: string;
  remark: string;
}
