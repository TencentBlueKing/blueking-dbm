import type { DetailBase, DetailClusters } from '../common';

/**
 * MySql 定点构造
 */

interface BackupLogRecord {
  backup_begin_time: string;
  backup_config_file: string;
  backup_consistent_time: string;
  backup_end_time: string;
  backup_host: string;
  backup_id: string;
  backup_meta_file: string;
  backup_port: string;
  backup_status: string;
  backup_time: string;
  backup_type: string;
  backup_dir: string;
  bill_id: string;
  binlog_info: {
    show_master_status: {
      binlog_file: string;
      binlog_pos: string;
      gtid: string;
      master_host: string;
      master_port: number;
    };
    show_slave_status: {
      binlog_file: string;
      binlog_pos: string;
      gtid: string;
      master_host: string;
      master_port: number;
    };
  };
  bk_biz_id: string;
  cluster_address: string;
  cluster_id: string;
  data_schema_grant: string;
  extra_fields: {
    backup_charset: string;
    encrypt_enable: boolean;
    storage_engine: string;
    time_zone: string;
    total_filesize: number;
    total_size_kb_uncompress: number;
    bk_cloud_id: number;
  };
  file_list: {
    contain_files: null;
    contain_tables: null;
    file_name: string;
    file_size: number;
    file_type: string;
    task_id: string;
  }[];
  index: {
    file_name: string;
  };
  instance_ip: string;
  instance_port: string;
  is_full_backup: string;
  mysql_role: string;
  mysql_version: string;
  server_id: string;
  shard_value: string;
}

export interface RollBackCluster extends DetailBase {
  clusters: DetailClusters;
  infos: {
    backup_source: string;
    cluster_id: number;
    databases: string[];
    databases_ignore: string[];
    tables: string[];
    tables_ignore: string[];
    rollback_host: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
    rollback_time: string;
    backupinfo: BackupLogRecord;
  }[];
}
