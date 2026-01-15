export default class BackupLogRecord {
  backup_begin_time: string;
  backup_config_file: string;
  backup_consistent_time: string;
  backup_dir: string;
  backup_end_time: string;
  backup_host: string;
  backup_id: string;
  backup_meta_file: string;
  /**
   * backup_method
    - full_by_ticket: 全库备份（单据）
    - partial_by_ticket: 库表备份（单据）
    - full_by_regular: 全库备份（例行）
    - non_full_by_regular: 非全库备份（例行）
   */
  backup_method: string;
  backup_port: number;
  backup_status: string;
  backup_time: string;
  backup_tool: string;
  backup_type: string;
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
  bk_biz_id: number;
  cluster_address: string;
  cluster_id: number;
  data_schema_grant: string;
  database_list: string[];
  extra_fields: {
    backup_charset: string;
    bk_cloud_id: number;
    encrypt_enable: boolean;
    storage_engine: string;
    time_zone: string;
    total_size_kb_uncompress: number;
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
  instance_port: number;
  is_full_backup: number;
  mysql_role: string;
  mysql_version: string;
  server_id: string;
  shard_value: string;
  total_filesize: number;

  constructor(payload = {} as BackupLogRecord) {
    this.backup_begin_time = payload.backup_begin_time || '';
    this.backup_config_file = payload.backup_config_file || '';
    this.backup_consistent_time = payload.backup_consistent_time || '';
    this.backup_dir = payload.backup_dir || '';
    this.backup_end_time = payload.backup_end_time || '';
    this.backup_host = payload.backup_host || '';
    this.backup_id = payload.backup_id || '';
    this.backup_meta_file = payload.backup_meta_file || '';
    this.backup_port = payload.backup_port || 0;
    this.backup_status = payload.backup_status || '';
    this.backup_method = payload.backup_method || '';
    this.backup_time = payload.backup_time || '';
    this.backup_type = payload.backup_type || '';
    this.bill_id = payload.bill_id || '';
    this.binlog_info = payload.binlog_info || {
      show_master_status: {
        binlog_file: '',
        binlog_pos: '',
        gtid: '',
        master_host: '',
        master_port: 0,
      },
      show_slave_status: {
        binlog_file: '',
        binlog_pos: '',
        gtid: '',
        master_host: '',
        master_port: 0,
      },
    };
    this.bk_biz_id = payload.bk_biz_id || 0;
    this.cluster_address = payload.cluster_address || '';
    this.cluster_id = payload.cluster_id || 0;
    this.backup_tool = payload.backup_tool || '';
    this.database_list = payload.database_list || [];
    this.data_schema_grant = payload.data_schema_grant || '';
    this.extra_fields = payload.extra_fields || {
      backup_charset: '',
      bk_cloud_id: 0,
      encrypt_enable: false,
      storage_engine: '',
      time_zone: '',
      total_size_kb_uncompress: 0,
    };
    this.total_filesize = payload.total_filesize || 0;
    this.backup_tool = payload.backup_tool || '';
    this.file_list = payload.file_list || [];
    this.index = payload.index || {
      file_name: '',
    };
    this.instance_ip = payload.instance_ip || '';
    this.instance_port = payload.instance_port || 0;
    this.is_full_backup = payload.is_full_backup || 0;
    this.mysql_role = payload.mysql_role || '';
    this.mysql_version = payload.mysql_version || '';
    this.server_id = payload.server_id || '';
    this.shard_value = payload.shard_value || '';
  }
}
