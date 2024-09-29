import type { DetailBase, DetailClusters, NodeInfo, SpecInfo } from '../common';

/**
 * TenDB Cluster 定点构造
 */

export interface RollBackCluster extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
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
  databases: string[];
  databases_ignore: string[];
  nodes: {
    backend_group: Record<string, NodeInfo>;
    spider: Record<string, NodeInfo>;
  };
  resource_request_id: string;
  rollback_time: string;
  rollback_type: string;
  specs: Record<string, SpecInfo>;
  tables: string[];
  tables_ignore: string[];
}
