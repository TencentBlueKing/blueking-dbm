import type { DetailBase, DetailClusters } from '../common';

export interface DbBackupDetails extends DetailBase {
  clusters: DetailClusters;
  file_tag: string;
  infos: {
    cluster_id: number;
  }[];
  oplog: boolean;
}
