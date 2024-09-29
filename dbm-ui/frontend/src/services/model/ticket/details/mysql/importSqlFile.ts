import type { DetailBase, DetailClusters } from '../common';

export interface ImportSqlFile extends DetailBase {
  backup: {
    backup_on: string;
    db_patterns: [];
    table_patterns: [];
  }[];
  bk_biz_id: number;
  blueking_language: string;
  charset: string;
  cluster_ids: number[];
  clusters: DetailClusters;
  created_by: string;
  execute_objects: {
    dbnames: [];
    ignore_dbnames: [];
    import_mode: string;
    sql_files: string[];
  }[];
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
  is_auto_commit: boolean;
  job_root_id: string;
  path: string;
  remark: string;
  root_id: string;
  sql_path: string;
  ticket_mode: {
    mode: string;
    trigger_time: string;
  };
}
