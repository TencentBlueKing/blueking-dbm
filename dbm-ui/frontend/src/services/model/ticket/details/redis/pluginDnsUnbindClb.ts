import type { DetailBase, DetailClusters } from '../common';

export interface PluginDnsUnbindClb extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
}
