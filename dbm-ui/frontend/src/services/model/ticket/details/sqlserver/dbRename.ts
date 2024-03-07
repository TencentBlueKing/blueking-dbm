import type { DetailBase, DetailClusters } from '../common';

export interface DbRename extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    from_database: string;
    to_database: string;
  }[];
}
