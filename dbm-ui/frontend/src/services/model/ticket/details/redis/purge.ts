import type { DetailBase, DetailClusters } from '../common';

export interface Purge extends DetailBase {
  clusters: DetailClusters;
  delete_type: string;
  rules: {
    backup: boolean;
    cluster_id: number;
    cluster_type: string;
    db_list: [];
    domain: string;
    flushall: true; // TODO: 目前都是 true, 后续根据后端实现调整
    force: boolean;
  }[];
}
