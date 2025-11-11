interface OriginBackupLogRecord {
  backup_begin_time: string;
  backup_config_file: string;
  backup_consistent_time: string;
  backup_dir: string;
  backup_end_time: string;
  backup_host: string;
  backup_id: string;
  backup_meta_file: string;
  backup_port: string;
  backup_status: string;
  /**
   * backup_method
    - full_by_ticket: 全库备份（单据）
    - partial_by_ticket: 库表备份（单据）
    - full_by_regular: 全库备份（例行）
    - non_full_by_regular: 非全库备份（例行）
   */
  backup_method: string;
  backup_time: string;
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
  bk_biz_id: string;
  cluster_address: string;
  cluster_id: string;
  database_list: string[];
  data_schema_grant: string;
  extra_fields: {
    backup_charset: string;
    bk_cloud_id: number;
    encrypt_enable: boolean;
    storage_engine: string;
    time_zone: string;
    total_size_kb_uncompress: number;
  };
  total_filesize: number;
  backup_tool: string;
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

export default class BackupLogRecord {
  cluster_id: number;
  bk_cloud_id: number;
  bk_biz_id: number;
  bill_id: string;
  cluster_address: string;
  database_list: string[];
  backup_method_list: string[];
  backup_tool_list: string[];
  backup_type_list: string[];
  total_filesize: number;
  backup_method: string;
  spider_node: OriginBackupLogRecord;
  tdbctl_node: OriginBackupLogRecord;
  remote_node: OriginBackupLogRecord;
  backup_consistent_time: string;
  backup_id: string;
  shard_list: string[];
  backup_type: string;
  backup_tool: string;

  constructor(payload = {} as BackupLogRecord) {
    this.cluster_id = payload.cluster_id || 0;
    this.bk_cloud_id = payload.bk_cloud_id || 0;
    this.bk_biz_id = payload.bk_biz_id || 0;
    this.bill_id = payload.bill_id || '';
    this.cluster_address = payload.cluster_address || '';
    this.database_list = payload.database_list || [];
    this.backup_method_list = payload.backup_method_list || [];
    this.backup_tool_list = payload.backup_tool_list || [];
    this.backup_type_list = payload.backup_type_list || [];
    this.total_filesize = payload.total_filesize || 0;
    this.backup_method = payload.backup_method || '';
    this.spider_node = payload.spider_node || {};
    this.tdbctl_node = payload.tdbctl_node || {};
    this.remote_node = payload.remote_node || {};
    this.backup_consistent_time = payload.backup_consistent_time || '';
    this.backup_id = payload.backup_id || '';
    this.shard_list = payload.shard_list || [];
    this.backup_type = payload.backup_type || '';
    this.backup_tool = payload.backup_tool || '';
  }
}
