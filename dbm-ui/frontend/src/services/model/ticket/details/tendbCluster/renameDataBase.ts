import type { DetailBase, DetailClusters } from '../common';

/**
 *  TenDB Cluster DB 重命名
 */

export interface RenameDataBase extends DetailBase {
  clusters: DetailClusters;
  force: boolean;
  infos: {
    cluster_id: number;
    from_database: string;
    to_database: string;
  }[];
}
