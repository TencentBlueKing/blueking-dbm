import type { DetailBase, DetailClusters } from '../common';

export interface DataExport extends DetailBase {
  clusters: DetailClusters;
  exported_files: Record<number, { file_name: string; file_path: string; size: number }>;
  infos: {
    cluster_id: number;
    export_options: {
      format: 'json' | 'bson';
      query: string;
    };
    ns_filter: {
      db_patterns: string[];
      ignore_dbs: string[];
      ignore_tables: string[];
      table_patterns: string[];
    };
  }[];
}
