import type { DetailBase, DetailClusters } from '../common';

export interface DumpData extends DetailBase {
  charset: string;
  cluster_id: number;
  clusters: DetailClusters;
  databases: string[];
  dump_data: boolean; // 是否导出表数据
  dump_schema: boolean; // 是否导出表结构
  tables: string[];
  tables_ignore: string[];
  where: string;
}
