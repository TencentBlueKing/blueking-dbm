import type { DetailBase, DetailClusters } from '../common';

export interface ExecScriptApply extends DetailBase {
  clusters: DetailClusters;
  cluster_ids: number[];
  mode: string;
  scripts: {
    name: string;
    content: string;
  }[];
}
