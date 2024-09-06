import type { DetailBase, DetailClusters } from './common';
import type { RollbackClusterTypes, RollbackHost } from './mysql';

/**
 * Spider 定点回档
 */
export interface SpiderRollbackDetails extends DetailBase {
  clusters: DetailClusters;
  infos: {
    backup_source: string;
    cluster_id: number;
    databases: string[];
    databases_ignore: string[];
    tables: string[];
    tables_ignore: string[];
    rollback_host: {
      // 接入层
      spider_host: RollbackHost;
      // 存储层
      remote_hosts: RollbackHost[];
    };
    target_cluster_id: number;
    rollback_type: string;
    rollback_time: string;
    backupinfo: {
      backup_id: string;
      backup_time: string;
      backup_type: string;
    };
  }[];
  rollback_cluster_type: RollbackClusterTypes;
}
