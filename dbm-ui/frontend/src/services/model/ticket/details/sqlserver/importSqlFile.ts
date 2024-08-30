import type { DetailBase, DetailClusters } from '../common';

export interface ImportSqlFile extends DetailBase {
  uid: string;
  backup: {
    backup_on: string;
    db_patterns: [];
    table_patterns: [];
  }[];
  backup_place: string;
  charset: string;
  cluster_ids: number[];
  clusters: DetailClusters;
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
  file_tag: string;
  force: boolean;
  path: string;
  ticket_mode: {
    mode: string;
    trigger_time: string;
  };
}
