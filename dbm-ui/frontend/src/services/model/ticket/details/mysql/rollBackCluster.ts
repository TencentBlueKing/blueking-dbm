import type { DetailBase, DetailClusters } from '../common';

/**
 * MySql 定点构造
 */
export interface RollbackCluster extends DetailBase {
  clusters: DetailClusters;
  infos: {
    backup_source: string;
    backupinfo: {
      backup_id: string;
      backup_time: string;
      backup_type: string;
      master_host: string;
      master_port: number;
      mysql_host: string;
      mysql_port: number;
      mysql_role: string;
    };
    cluster_id: number;
    databases: string[];
    databases_ignore: string[];
    rollback_host: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
    rollback_time: string;
    rollback_type: string;
    tables: string[];
    tables_ignore: string[];
    target_cluster_id: number;
  }[];
  rollback_cluster_type: 'BUILD_INTO_NEW_CLUSTER' | 'BUILD_INTO_EXIST_CLUSTER' | 'BUILD_INTO_METACLUSTER';
}
