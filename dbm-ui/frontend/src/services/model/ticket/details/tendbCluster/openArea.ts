import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL 开区
 */

export interface OpenArea extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
  config_data: {
    cluster_id: number;
    execute_objects: {
      data_tblist: string[];
      schema_tblist: string[];
      source_db: string;
      target_db: string;
    }[];
  }[];
  config_id: number;
  force: boolean;
  rules_set: {
    account_rules: {
      bk_biz_id: number;
      dbname: string;
    }[];
    cluster_type: string;
    source_ips: string[];
    target_instances: string[];
    user: string;
  }[];
}
