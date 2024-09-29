import type { DetailBase, DetailClusters } from '../common';

export interface PluginDeleteClb extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
}
