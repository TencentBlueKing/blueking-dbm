import type { DetailBase, DetailClusters } from '../common';

export interface ImportSqlFile extends DetailBase {
  uid: string;
  path: string;
  backup: {
    backup_on: string;
    db_patterns: [];
    table_patterns: [];
  }[];
  charset: string;
  root_id: string;
  bk_biz_id: number;
  created_by: string;
  cluster_ids: number[];
  clusters: DetailClusters;
  grammar_check_info: Record<
    string,
    {
      highrisk_warnings: {
        command_type: string;
        line: number;
        sqltext: string;
        warn_info: string;
      }[];
    }
  >;
  ticket_mode: {
    mode: string;
    trigger_time: string;
  };
  ticket_type: string;
  execute_objects: {
    dbnames: [];
    ignore_dbnames: [];
    import_mode: string;
    sql_files: string[];
  }[];
  import_mode: string;
  semantic_node_id: string;
  dump_file_path?: string;
}
