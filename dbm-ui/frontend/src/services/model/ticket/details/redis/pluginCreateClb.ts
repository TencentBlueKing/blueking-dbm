import type { DetailBase, DetailClusters } from '../common';

export interface PluginCreateClb extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
}
