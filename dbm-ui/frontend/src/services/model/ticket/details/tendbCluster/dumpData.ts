import type { DetailBase, DetailClusters } from '../common';

export interface DumpData extends DetailBase {
  clusters: DetailClusters;
  cluster_id: number;
  charset: string;
  databases: string[];
  tables: string[];
  tables_ignore: string[];
  where: string;
  dump_data: boolean; // 是否导出表数据
  dump_schema: boolean; // 是否导出表结构
}
