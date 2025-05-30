import type { DetailBase, DetailClusters } from '../common';

export interface PluginCreatePolaris extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
}
