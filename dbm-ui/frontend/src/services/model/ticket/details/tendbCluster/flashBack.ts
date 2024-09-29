import type { DetailBase, DetailClusters } from '../common';

/**
 * TenDB Cluster 闪回
 */

export interface FlashBack extends DetailBase {
  clusters: DetailClusters;
  force: boolean;
  infos: {
    cluster_id: number;
    databases: string[];
    databases_ignore: string[];
    end_time: string;
    message: string;
    mysqlbinlog_rollback: string;
    recored_file: string;
    start_time: string;
    tables: string[];
    tables_ignore: string[];
  }[];
}
