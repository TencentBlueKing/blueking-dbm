import type { DetailBase, DetailClusters } from '../common';

export interface ExecScriptApply extends DetailBase {
  cluster_ids: number[];
  clusters: DetailClusters;
  mode: 'manual' | 'file';
  // 新协议：走制品库路径
  path: string;
  // 新协议：走制品库路径
  script_files: string[];
  // 旧协议
  scripts?: {
    content: string;
    name: string;
  }[];
}
