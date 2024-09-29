import type { DetailBase, DetailClusters } from '../common';

/**
 * TenDB Cluster 定点构造
 */

export interface RollbackCluster extends DetailBase {
  apply_details: {
    bk_cloud_id: number;
    charset: string;
    city: string;
    cluster_name: string;
    cluster_shard_num: number;
    db_app_abbr: string;
    db_version: string;
    immutable_domain: string;
    ip_source: string;
    module: number;
    remote_shard_num: number;
    resource_spec: {
      backend_group: {
        count: number;
        spec_id: number;
      };
      spider: {
        count: number;
        spec_id: number;
      };
    };
    spider_port: number;
    spider_version: string;
  };
  clusters: DetailClusters;
  ignore_check_db: boolean;
  infos: {
    backupinfo: {
      backup_begin_time: string;
      backup_end_time: string;
      backup_host: string;
      backup_id: string;
      backup_time: string;
      bill_id: string;
      bk_biz_id: string;
      bk_cloud_id: string;
      cluster_address: string;
      cluster_id: number;
      remote_node: Record<string, any>;
      spider_node: Record<string, any>;
      spider_slave: Record<string, any>;
      time_zone: string;
    };
    cluster_id: number;
    databases: string[];
    databases_ignore: string[];
    rollback_host: {
      remote_hosts: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
      spider_host: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      };
    };
    rollback_time: string;
    rollback_type: string;
    tables: string[];
    tables_ignore: string[];
    target_cluster_id: number;
  }[];
  rollback_cluster_type: string;
}
