/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package models

// Config information
type Config struct {
	MySQLInstances  []MySQLConfig `json:"mysql_instances"`
	OutputFile      string        `json:"output_file"`
	IntervalSeconds int           `json:"interval_seconds"`
}

// MySQLConfig MySQL config
type MySQLConfig struct {
	InstanceName string `json:"instance_name"`
	Host         string `json:"host"`
	Port         int    `json:"port"`
	User         string `json:"user"`
	Password     string `json:"password"`
	DBName       string `json:"dbname"`
}

// AllMetrics contains system and databases metrics
type AllMetrics struct {
	Timestamp int64                      `json:"timestamp"`
	ServiceID int64                      `json:"service_id"`
	System    SystemMetrics              `json:"system"`
	Databases map[string]DatabaseMetrics `json:"databases"`
}

// SystemMetrics System metrics
type SystemMetrics struct {
	// CPU metrics
	CPUUsagePercent  float64 `json:"cpu_usage_percent"`
	CPUUserPercent   float64 `json:"cpu_user_percent"`
	CPUSystemPercent float64 `json:"cpu_system_percent"`
	CPUIOWaitPercent float64 `json:"cpu_iowait_percent"`
	CPULoad1         float64 `json:"cpu_load_1"`
	CPULoad5         float64 `json:"cpu_load_5"`
	CPULoad15        float64 `json:"cpu_load_15"`

	// Mem metrics
	MemTotalMB     uint64 `json:"mem_total_mb"`
	MemUsedMB      uint64 `json:"mem_used_mb"`
	MemFreeMB      uint64 `json:"mem_free_mb"`
	MemCacheMB     uint64 `json:"mem_cache_mb"`
	MemAvailableMB uint64 `json:"mem_available_mb"`
	SwapTotalMB    uint64 `json:"swap_total_mb"`
	SwapUsedMB     uint64 `json:"swap_used_mb"`

	// Disk metrics
	DiskUsagePercent float64 `json:"disk_usage_percent"`
	DiskTotal        uint64  `json:"disk_total"`
	DiskUsed         uint64  `json:"disk_used"`
	DiskAvailable    uint64  `json:"disk_available"`
	DiskReadOnly     bool    `json:"disk_read_only"`

	// Network metrics
	NetIpAddress      string  `json:"network_ip_address"`
	NetBytesIn        uint64  `json:"network_bytes_in"`
	NetBytesOut       uint64  `json:"network_bytes_out"`
	NetUsage          string  `json:"network_usage"`
	NetTCPConnections int     `json:"network_tcp_connections"`
	NetPacketLossIn   float64 `json:"network_packet_loss_in"`
	NetPacketLossOut  float64 `json:"network_packet_loss_out"`
}

// DatabaseMetrics Databases metrics
type DatabaseMetrics struct {

	// MySQLStatus MySQL status
	Version          string  `json:"mysql_version"`
	ThreadID         string  `json:"mysql_connected_thread_id"`
	CurrentDatabase  string  `json:"mysql_current_database"`
	CurrentUser      string  `json:"mysql_current_user"`
	ThreadsConnected int     `json:"mysql_threads_connected"`
	ServerCharset    string  `json:"mysql_server_charset"`
	OpenTablesTotal  int     `json:"mysql_open_tables_total"`
	FlushTables      int     `json:"mysql_flush_tables"`
	OpenTablesNow    int     `json:"mysql_open_tables_now"`
	SlowQueriesNow   int     `json:"mysql_slow_queries_now"`
	TotalQuestions   int     `json:"mysql_total_questions"`
	QueriesPerSecond float64 `json:"mysql_avg_qps"`

	// MySQLPerformance MySQL Performance metrics

	// MySQL Performance Connection metrics
	ThreadsRunning            int `json:"mysql_threads_running"`
	ConnectionsAborted        int `json:"mysql_connections_aborted"`
	Connections               int `json:"mysql_connections"`
	ConnectionsErrorsAccept   int `json:"mysql_connections_errors_accept"`
	ConnectionsErrorsInternal int `json:"mysql_connections_errors_internal"`
	ConnectionsErrorsPeerAddr int `json:"mysql_connections_errors_peer_address"`

	// MySQL Performance Query metrics
	QueryTotal     int64 `json:"mysql_query_total"`
	QPS            int   `json:"mysql_QPS"`
	TPS            int   `json:"mysql_TPS"`
	QueryQuestions int64 `json:"mysql_questions_total"`
	QuerySelects   int64 `json:"mysql_selects_times"`
	QueryInserts   int64 `json:"mysql_inserts_times"`
	QueryUpdates   int64 `json:"mysql_updates_times"`
	QueryDeletes   int64 `json:"mysql_deletes_times"`
	QuerySlow      int64 `json:"mysql_slow_queries_times"`

	// MySQL Performance Query Cache metrics
	KeyReadRequests   int64   `json:"key_read_requests"`
	KeyReads          int64   `json:"key_reads"`
	KeyBufferHitRate  float64 `json:"key_buffer_hit_rate"`
	QCacheHits        int64   `json:"query_cache_hits"`
	QCacheFreeBlocks  int64   `json:"query_cache_free_blocks"`
	QCacheFreeMem     int64   `json:"query_cache_free_mem"`
	QCacheInserts     int64   `json:"query_cache_inserts"`
	QCachePrunes      int64   `json:"query_cache_lowmen_prunes"`
	QCacheNotCached   int64   `json:"query_cache_not_cached"`
	QCacheTotalBlocks int64   `json:"query_cache_total_blocks"`

	// MySQL Performance InnoDB handler metrics
	HandlerReadKey      int64 `json:"handler_read_key"`
	HandlerReadRndNext  int64 `json:"handler_read_rnd_next"`
	HandlerWrite        int64 `json:"handler_write"`
	HandlerPrepare      int64 `json:"handler_prepare"`
	HandlerCommit       int64 `json:"handler_commit"`
	HandlerExternalLock int64 `json:"handler_external_lock"`

	//  MySQL Performance InnoDB metrics
	InnodbBackgroundLogSync       int64   `json:"innodb_background_log_sync"`
	InnodbLogWriteRequests        int64   `json:"innodb_log_write_requests"`
	InnodbLogWrites               int64   `json:"innodb_log_write_times"`
	InnodbOsLogFsyncs             int64   `json:"innodb_os_log_fsyncs"`
	InnodbBufferPoolPagesDirty    int64   `json:"innodb_buffer_pool_pages_dirty"`
	InnodbBufferPoolPagesFlushed  int64   `json:"innodb_buffer_pool_pages_flushed"`
	InnodbBufferPoolPagesTotal    int64   `json:"innodb_buffer_pool_pages_total"`
	InnodbBufferPoolPagesFree     int64   `json:"innodb_buffer_pool_pages_free"`
	InnodbBufferPoolPagesData     int64   `json:"innodb_buffer_pool_pages_pages_data"`
	InnodbBufferPoolBytesData     int64   `json:"innodb_buffer_pool_pages_bytes_data"`
	InnodbBufferPoolWriteRequests int64   `json:"innodb_buffer_pool_write_requests"`
	InnodbBufferPoolReadRequests  int64   `json:"innodb_buffer_pool_reads_requests"`
	InnodbBufferPoolHitRate       float64 `json:"innodb_buffer_pool_hit_rate"`
	InnodbRowsRead                int64   `json:"innodb_row_reads"`
	InnodbRowsInserted            int64   `json:"innodb_row_inserted"`
	InnodbRowsUpdated             int64   `json:"innodb_row_updated"`
	InnodbRowsDeleted             int64   `json:"innodb_row_deleted"`
	InnodbDataWrites              int64   `json:"innodb_data_written"`
	InnodbDblwrPagesWritten       int64   `json:"innodb_dblwr_pages_written"`
	InnodbRowLockWaitsTime        int64   `json:"innodb_row_lock_waits_time"`
	InnodbTableLockWaitsNum       int64   `json:"innodb_table_lock_waits_num"`
	InnodbRowLockWaitsNum         int64   `json:"innodb_row_lock_waits_num"`

	// MySQL Performance Table statistical metrics
	TableCreatedTmp     int64 `json:"tables_created_tmp"`
	TableCreatedTmpDisk int64 `json:"tables_created_tmp_disk"`
	FileCreatedTmp      int64 `json:"files_created_tmp"`
	FileOpen            int64 `json:"files_opened"`
	TableOpen           int64 `json:"tables_opened"`

	// MySQL Performance BinLog metrics
	BinlogCacheDiskUse     int64 `json:"binlog_cache_disk_use"`
	BinlogCacheUse         int64 `json:"binlog_cache_use"`
	BinlogStmtCacheDiskUse int64 `json:"binlog_stmt_cache_disk_use"`
	BinlogStmtCacheUse     int64 `json:"binlog_stmt_cache_use"`

	// MySQL Performance Performance schema metrics
	SchemaAccountsLost        int64 `json:"performance_schema_accounts_lost"`
	SchemaCondClassesLost     int64 `json:"performance_schema_cond_classes_lost"`
	SchemaFileHandlesLost     int64 `json:"performance_schema_file_handles_lost"`
	SchemaLockerLost          int64 `json:"performance_schema_locker_lost"`
	SchemaDigestLost          int64 `json:"performance_schema_digest_lost"`
	SchemaRwlockInstancesLost int64 `json:"performance_schema_rwlock_instances_lost"`
	SchemaThreadInstancesLost int64 `json:"performance_schema_thread_instances_lost"`
	SchemaTableLockStatLost   int64 `json:"performance_schema_table_lock_stat_lost"`
}
