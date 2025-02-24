import type { DetailBase, DetailClusters } from '../common';

export interface ExecScriptApply extends DetailBase {
  cluster_ids: number[];
  clusters: DetailClusters;
  mode: string;
  scripts: {
    content: string;
    name: string;
  }[];
}
