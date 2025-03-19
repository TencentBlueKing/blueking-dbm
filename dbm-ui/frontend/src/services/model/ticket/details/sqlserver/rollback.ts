import type { DetailBase, DetailClusters } from '../common';

export interface Rollback extends DetailBase {
  clusters: DetailClusters;
  infos: {
    db_list: string[];
    dst_cluster: number;
    ignore_db_list: string[];
    rename_infos: {
      db_name: string;
      old_db_name: string;
      rename_db_name: string;
      target_db_name: string;
    }[];
    restore_backup_file: {
      backup_id: string;
      logs: {
        backup_begin_time: string;
        backup_end_time: string;
        backup_host: string;
        backup_id: string;
        backup_port: number;
        backup_task_end_time: string;
        backup_task_start_time: string;
        backup_type: string;
        bill_id: string;
        bk_biz_id: number;
        bk_cloud_id: number;
        charset: string;
        checkpointlsn: number;
        cluster_address: string;
        cluster_id: number;
        compatibility_level: number;
        data_schema_grant: string;
        databasebackuplsn: number;
        db_list: string;
        db_size_kb: number;
        dbname: string;
        file_cnt: number;
        file_name: string;
        file_size_kb: number;
        firstlsn: number;
        is_full_backup: boolean;
        lastlsn: number;
        local_path: string;
        master_ip: string;
        master_port: number;
        role: string;
        task_id: string;
        time_zone: string;
        version: string;
      }[];
    };
    restore_time: string;
    src_cluster: number;
  }[];
  is_local: boolean;
}
