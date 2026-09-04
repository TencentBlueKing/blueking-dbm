import type { DetailBase } from '../common';

/**
 * VictoriaMetrics 查询集群部署
 */
export interface QueryApply extends DetailBase {
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
      component_name: 'vmselect';
      env: {
        EXTRA_ARGS: {
          storageNode: string;
        };
      };
      replicas: number;
      request_cpu: string;

      request_memory: string;
      version: string;
    },
  ];
  created_by: string;
  creator: string;
  db_app_abbr: string;
  db_version: string; // 小版本
  k8s_cluster_name: string;
  major_version: string; // 大版本
  remark: string;
  // storage_nodes: string;
}
