import type { DetailBase, DetailClusters } from '../common';

export interface DataExport extends DetailBase {
  cluster_ids: number[];
  clusters: DetailClusters;
  execute_objects: {
    dbnames: string[];
    sql: string;
  }[];
  select_role?: string;
}
