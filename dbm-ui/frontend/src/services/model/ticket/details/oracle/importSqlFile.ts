import type { DetailBase, DetailClusters } from '../common';

export interface ImportSqlFile extends DetailBase {
  cluster_info: {
    cluster_id: number;
    execute_db: string[];
  }[];
  clusters: DetailClusters;
  import_mode: string; // 展示字段
  path: string; // 文件路径，用于内容回显
  script_files: string[];
}
