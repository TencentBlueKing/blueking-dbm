
# dbactuator mysql deploy 
安装mysql  
`dbactuator mysql deploy -u xx -n xx -p <base64(payload)> `   
前置工作
-  先运行 dbactuator sys init
-  将 mysql-5.7.20-linux-x86_64-tmysql-3.3-gcs.tar.gz 下载到 /data/install



### 原始 payload 
```
{
    "general": {
       "runtime_account":{
        "admin_user":"xx",
        "admin_pwd": "xx",
        "monitor_user":"xx",
        "monitor_pwd":"xx",
        "monitor_access_all_user":"xx",
        "monitor_access_all_pwd":"xx",
        "repl_user":"xx",
        "repl_pwd":"xx",
        "backup_user":"xx",
        "backup_pwd":"xx",
        "yw_user":"xx",
        "yw_pwd": "xx"
        "proxy_admin_user": "xx",
        "proxy_admin_pwd": "xx"
     }
    },
    "extend": {
        "host": "127.0.0.1",
        "pkg": "mysql-5.7.20-linux-x86_64-tmysql-3.3-gcs.tar.gz",
        "pkg_md5": "ea15cee9abf6f11859b2144352f684c9",
        "mysql_version": "5.7.20",
        "charset": "utf8mb4",
        "start_port": 20000,
        "inst_num": 1,
        "mycnf_configs": {
            "client": {
                "default-character-set": "{{mysqld.character_set_server}}",
                "port": "{{mysqld.port}}",
                "socket": "{{mysqld.datadir}}/mysql.sock"
            },
            "mysql": {
                "default-character-set": "{{mysqld.character_set_server}}",
                "no-auto-rehash": "1",
                "port": "{{mysqld.port}}",
                "socket": "{{mysqld.datadir}}/mysql.sock"
            },
            "mysqld": {
                "bind-address": "{{mysqld.bind-address}}",
                "binlog_format": "ROW",
                "character_set_server": "{{mysqld.character_set_server}}",
                "datadir": "{{mysqld.datadir}}/data",
                "default-storage-engine": "InnoDB",
                "default_time_zone": "+08:00",
                "expire_logs_days": "60",
                "init_connect": "insert into test.conn_log values(connection_id(),now(),user(),current_user(),null);",
                "innodb_buffer_pool_instances": "4",
                "innodb_buffer_pool_size": "{{mysqld.innodb_buffer_pool_size}}",
                "innodb_data_file_path": "ibdata1:1G:autoextend",
                "innodb_data_home_dir": "{{mysqld.datadir}}/innodb/data",
                "innodb_file_format": "Barracuda",
                "innodb_file_per_table": "1",
                "innodb_flush_log_at_trx_commit": "0",
                "innodb_io_capacity": "1000",
                "innodb_lock_wait_timeout": "50",
                "innodb_log_buffer_size": "32M",
                "innodb_log_file_size": "256M",
                "innodb_log_files_in_group": "4",
                "innodb_log_group_home_dir": "{{mysqld.datadir}}/innodb/log",
                "innodb_read_io_threads": "8",
                "innodb_thread_concurrency": "16",
                "innodb_write_io_threads": "8",
                "interactive_timeout": "86400",
                "log_bin": "{{mysqld.logdir}}/binlog/binlog{{port}}.bin",
                "log_bin_compress": "OFF",
                "log_bin_trust_function_creators": "1",
                "log_slave_updates": "1",
                "log_warnings": "0",
                "long_query_time": "1",
                "lower_case_table_names": "0",
                "max_allowed_packet": "128m",
                "max_binlog_cache_size": "128M",
                "max_binlog_size": "256M",
                "max_connect_errors": "99999999",
                "max_connections": "6000",
                "performance_schema": "OFF",
                "port": "{{mysqld.port}}",
                "query_cache_size": "0",
                "query_cache_type": "0",
                "query_response_time_stats": "ON",
                "relay-log": "{{mysqld.datadir}}/relay-log/relay-log.bin",
                "relay_log_recovery": "1",
                "relay_log_uncompress": "OFF",
                "server_id": "{{mysqld.server_id}}",
                "show_compatibility_56": "ON",
                "skip-name-resolve": "1",
                "slave_compressed_protocol": "1",
                "slave_exec_mode": "STRICT",
                "slave_parallel_type": "DATABASE",
                "slave_parallel_workers": "4",
                "slow_query_log": "1",
                "slow_query_log_file": "{{mysqld.logdir}}/slow-query.log",
                "socket": "{{mysqld.datadir}}/mysql.sock",
                "sort_buffer_size": "2M",
                "sql_mode": "''",
                "stored_program_cache": "1024",
                "sync_binlog": "0",
                "table_open_cache": "5120",
                "thread_cache_size": "8",
                "tmpdir": "{{mysqld.datadir}}/tmp",
                "transaction_isolation": "REPEATABLE-READ",
                "wait_timeout": "86400"
            },
            "mysqldump": {
                "max_allowed_packet": "1G",
                "quick": "1"
            }
        }
    }
}
```