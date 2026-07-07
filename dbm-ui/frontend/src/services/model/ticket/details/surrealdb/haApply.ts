import type { DetailBase } from '../common';

/**
 * SurrealDB 集群部署
 */
export interface HaApply extends DetailBase {
  bk_biz_name: string;
  bk_cloud_id: number;
  bk_cloud_region: string;
  city_code: string;
  city_name: string; // 展示字段
  cluster_alias: string;
  cluster_name: string;
  cluster_type: string;
  component_list: [
    {
      component_name: 'surreal';
      replicas: number;
      request_cpu: string;
      request_memory: string;
    },
    {
      component_name: 'pd';
      replicas: number;
      request_cpu: string;
      request_memory: string;
      storage: string;
    },
    {
      component_name: 'tikv';
      replicas: number;
      request_cpu: string;
      request_memory: string;
      storage: string;
    },
  ];
  creator: string;
  db_app_abbr: string;
  db_version: string; // 小版本
  k8s_cluster_name: string;
  major_version: string; // 大版本
  remark: string;
}
