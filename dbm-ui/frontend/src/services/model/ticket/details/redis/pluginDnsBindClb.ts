import type { DetailBase, DetailClusters } from '../common';

export interface PluginDnsBindClb extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
}
