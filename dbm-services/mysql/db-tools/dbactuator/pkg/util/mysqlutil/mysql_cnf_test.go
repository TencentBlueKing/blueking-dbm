package mysqlutil_test

import (
	"testing"
)

// go test -v   pkg/util/mysqlutil/mysql_cnf*
func TestGenerateMycnf(t *testing.T) {
	t.Logf("start ...")
	input := `{
		"client": {
			"port": "3306",
			"socket": "mysqldata/mysql.sock"
		},
		"mysql": {
			"default-character-set": "utf-8",
			"no_auto_rehash": "ON",
			"port": "3306",
			"socket": "mysqldata/mysql.sock"
		},
		"mysqld": {
			"max_connect_errors":"99999",
			"skip_symbolic_links":"ON",
			"init_connect":"\"set @user=user(),@cur_user=current_user(); insert into test.conn_log values(connection_id(),now(),@user,@cur_user,'127.0.0.1');\"",
			"skip_name_resolve":"ON",
			"bind_address":"127.0.0.1",
			"binlog_format":"ROW",
			"character_set_server":"utf8",
			"datadir":"/data1/mysqldata/20001/data",
			"default_storage_engine":"innodb",
			"innodb_buffer_pool_size":"2150M",
			"innodb_data_home_dir":"/data1/mysqldata/20001/innodb/data",
			"innodb_file_format":"Barracuda",
			"innodb_file_per_table":"1",
			"innodb_flush_log_at_trx_commit":"0",
			"innodb_flush_method":"O_DIRECT",
			"innodb_io_capacity":"1000",
			"innodb_lock_wait_timeout":"50",
			"innodb_log_buffer_size":"32M",
			"innodb_log_file_size":"268435456",
			"innodb_log_files_in_group":"4",
			"innodb_log_group_home_dir":"/data1/mysqldata/20001/innodb/log",
			"innodb_read_io_threads":"4",
			"innodb_thread_concurrency":"16",
			"innodb_write_io_threads":"4",
			"interactive_timeout":"86400",
			"key_buffer_size":"64M",
			"log_bin":"/data/mysqllog/20001/binlog/binlog20001.bin",
			"log_bin_trust_function_creators":"1",
			"log_slave_updates":"1",
			"log_warnings":"0",
			"long_query_time":"1",
			"max_allowed_packet":"64M",
			"max_binlog_size":"256M",
			"max_connect_errors":"99999999",
			"max_connections":"3000",
			"myisam_sort_buffer_size":"64M",
			"port":"20001",
			"query_cache_size":"0",
			"query_cache_type":"0",
			"read_buffer_size":"2M",
			"relay_log":"/data1/mysqldata/20001/relay-log/relay-log.bin",
			"replicate_wild_ignore_table":"mysql.%;test.conn_log",
			"server_id":"104544287",
			"skip_external_locking":"ON",
			"skip_symbolic_links":"ON",
			"slow_query_log":"1",
			"slow_query_log_file":"/data/mysqllog/20001/slow-query.log",
			"socket":"/data1/mysqldata/20001/mysql.sock",
			"sort_buffer_size":"2M",
			"tmpdir":"/data1/mysqldata/20001/tmp",
			"wait_timeout":"86400",
			"sql_mode":""
		},
		"mysqldump": {
			"max_allowed_packet": "64M",
			"quick": "ON"
		},
		"mysqld-5.5": {
			"innodb_additional_mem_pool_size": "20M"
		}
	 }`
	t.Log(input)
}
