import type { DetailBase, DetailClusters } from '../common';

export interface ImportSqlFile extends DetailBase {
  backup: {
    backup_on: string;
    db_patterns: string[];
    table_patterns: string[];
  }[];
  bk_biz_id: number;
  blueking_language: string;
  charset: string;
  cluster_ids: number[];
  clusters: DetailClusters;
  created_by: string;
  execute_objects: {
    dbnames: string[];
    ignore_dbnames: string[];
    import_mode: 'manual' | 'file';
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
