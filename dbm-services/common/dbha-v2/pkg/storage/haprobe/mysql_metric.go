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

package haprobe

// HostMetric host metric
type HostMetric struct {
	// CPU
	CPUUsagePercent  float64 `json:"cpu_usage_percent"`
	CPUUserPercent   float64 `json:"cpu_user_percent"`
	CPUSystemPercent float64 `json:"cpu_system_percent"`
	CPUIOWaitPercent float64 `json:"cpu_iowait_percent"`
	CPULoad1         float64 `json:"cpu_load_1"`
	CPULoad5         float64 `json:"cpu_load_5"`
	CPULoad15        float64 `json:"cpu_load_15"`

	// Mem
	MemTotalMB     uint64 `json:"mem_total_mb"`
	MemUsedMB      uint64 `json:"mem_used_mb"`
	MemFreeMB      uint64 `json:"mem_free_mb"`
	MemCacheMB     uint64 `json:"mem_cache_mb"`
	MemAvailableMB uint64 `json:"mem_available_mb"`
	SwapTotalMB    uint64 `json:"swap_total_mb"`
	SwapUsedMB     uint64 `json:"swap_used_mb"`

	// Disk
	DiskUsagePercent float64 `json:"disk_usage_percent"`
	DiskTotal        uint64  `json:"disk_total"`
	DiskUsed         uint64  `json:"disk_used"`
	DiskAvailable    uint64  `json:"disk_available"`
	DiskReadOnly     bool    `json:"disk_read_only"`

	// Network
	NetIpAddress      string  `json:"network_ip_address"`
	NetBytesIn        uint64  `json:"network_bytes_in"`
	NetBytesOut       uint64  `json:"network_bytes_out"`
	NetUsage          string  `json:"network_usage"`
	NetTCPConnections uint    `json:"network_tcp_connections"`
	NetPacketLossIn   float64 `json:"network_packet_loss_in"`
	NetPacketLossOut  float64 `json:"network_packet_loss_out"`
}

// InnoDBMetric InnoDB performance metrics
type InnoDBMetric struct {
	InnodbBackgroundLogSync       uint64  `json:"innodb_background_log_sync"`
	InnodbLogWriteRequests        uint64  `json:"innodb_log_write_requests"`
	InnodbLogWrites               uint64  `json:"innodb_log_write_times"`
	InnodbOsLogFsyncs             uint64  `json:"innodb_os_log_fsyncs"`
	InnodbBufferPoolPagesDirty    uint64  `json:"innodb_buffer_pool_pages_dirty"`
	InnodbBufferPoolPagesFlushed  uint64  `json:"innodb_buffer_pool_pages_flushed"`
	InnodbBufferPoolPagesTotal    uint64  `json:"innodb_buffer_pool_pages_total"`
	InnodbBufferPoolPagesFree     uint64  `json:"innodb_buffer_pool_pages_free"`
	InnodbBufferPoolPagesData     uint64  `json:"innodb_buffer_pool_pages_pages_data"`
	InnodbBufferPoolBytesData     uint64  `json:"innodb_buffer_pool_pages_bytes_data"`
	InnodbBufferPoolWriteRequests uint64  `json:"innodb_buffer_pool_write_requests"`
	InnodbBufferPoolReadRequests  uint64  `json:"innodb_buffer_pool_reads_requests"`
	InnodbBufferPoolHitRate       float64 `json:"innodb_buffer_pool_hit_rate"`
	InnodbRowsRead                uint64  `json:"innodb_row_reads"`
	InnodbRowsInserted            uint64  `json:"innodb_row_inserted"`
	InnodbRowsUpdated             uint64  `json:"innodb_row_updated"`
	InnodbRowsDeleted             uint64  `json:"innodb_row_deleted"`
	InnodbDataWrites              uint64  `json:"innodb_data_written"`
	InnodbDblwrPagesWritten       uint64  `json:"innodb_dblwr_pages_written"`
	InnodbRowLockWaitsTime        uint64  `json:"innodb_row_lock_waits_time"`
	InnodbTableLockWaitsNum       uint64  `json:"innodb_table_lock_waits_num"`
	InnodbRowLockWaitsNum         uint64  `json:"innodb_row_lock_waits_num"`
}

// DatabaseMetric Databases metric
type DatabaseMetric struct {
	ListenPort int `json:"listen_port"`

	// Status
	Version          string  `json:"mysql_version"`
	ThreadID         string  `json:"mysql_connected_thread_id"`
	CurrentDatabase  string  `json:"mysql_current_database"`
	CurrentUser      string  `json:"mysql_current_user"`
	ThreadsConnected uint    `json:"mysql_threads_connected"`
	ServerCharset    string  `json:"mysql_server_charset"`
	OpenTablesTotal  uint    `json:"mysql_open_tables_total"`
	FlushTables      uint    `json:"mysql_flush_tables"`
	OpenTablesNow    uint    `json:"mysql_open_tables_now"`
	SlowQueriesNow   uint    `json:"mysql_slow_queries_now"`
	TotalQuestions   uint    `json:"mysql_total_questions"`
	QueriesPerSecond float64 `json:"mysql_avg_qps"`

	// Performance Connection metric
	ThreadsRunning            int `json:"mysql_threads_running"`
	ConnectionsAborted        int `json:"mysql_connections_aborted"`
	Connections               int `json:"mysql_connections"`
	ConnectionsErrorsAccept   int `json:"mysql_connections_errors_accept"`
	ConnectionsErrorsInternal int `json:"mysql_connections_errors_internal"`
	ConnectionsErrorsPeerAddr int `json:"mysql_connections_errors_peer_address"`

	// MySQL Performance Query metric
	QueryTotal     uint64 `json:"mysql_quey_total"`
	QPS            uint   `json:"mysql_QPS"`
	TPS            uint   `json:"mysql_TPS"`
	QueryQuestions uint64 `json:"mysql_questions_total"`
	QuerySelects   uint64 `json:"mysql_selects_times"`
	QueryInserts   uint64 `json:"mysql_inserts_times"`
	QueryUpdates   uint64 `json:"mysql_updates_times"`
	QueryDeletes   uint64 `json:"mysql_deletes_times"`
	QuerySlow      uint64 `json:"mysql_slow_queries_times"`

	// MySQL Performance Query Cache metric
	KeyReadRequests   uint64  `json:"key_read_requests"`
	KeyReads          uint64  `json:"key_reads"`
	KeyBufferHitRate  float64 `json:"key_buffer_hit_rate"`
	QCacheHits        uint64  `json:"query_cache_hits"`
	QCacheFreeBlocks  uint64  `json:"query_cache_free_blocks"`
	QCacheFreeMem     uint64  `json:"query_cache_free_mem"`
	QCacheInserts     uint64  `json:"query_cache_inserts"`
	QCachePrunes      uint64  `json:"query_cache_lowmen_prunes"`
	QCacheNotCached   uint64  `json:"query_cache_not_cached"`
	QCacheTotalBlocks uint64  `json:"query_cache_total_blocks"`

	// MySQL Performance InnoDB handler metrics
	HandlerReadKey      uint64 `json:"handler_read_key"`
	HandlerReadRndNext  uint64 `json:"handler_read_rnd_next"`
	HandlerWrite        uint64 `json:"handler_write"`
	HandlerPrepare      int64  `json:"handler_prepare"`
	HandlerCommit       uint64 `json:"handler_commit"`
	HandlerExternalLock uint64 `json:"handler_external_lock"`

	// Performance Table statistical metrics
	TableCreatedTmp     uint64 `json:"tables_created_tmp"`
	TableCreatedTmpDisk uint64 `json:"tables_created_tmp_disk"`
	FileCreatedTmp      uint64 `json:"files_created_tmp"`
	FileOpen            uint64 `json:"files_opened"`
	TableOpen           uint64 `json:"tables_opened"`

	// Performance BinLog metrics
	BinlogCacheDiskUse     uint64 `json:"binlog_cache_disk_use"`
	BinlogCacheUse         uint64 `json:"binlog_cache_use"`
	BinlogStmtCacheDiskUse uint64 `json:"binlog_stmt_cache_disk_use"`
	BinlogStmtCacheUse     uint64 `json:"binlog_stmt_cache_use"`

	// Performance Performance schema metrics
	SchemaAccountsLost        uint64 `json:"performance_schema_accounts_lost"`
	SchemaCondClassesLost     uint64 `json:"performance_schema_cond_classes_lost"`
	SchemaFileHandlesLost     uint64 `json:"performance_schema_file_handles_lost"`
	SchemaLockerLost          uint64 `json:"performance_schema_locker_lost"`
	SchemaDigestLost          uint64 `json:"performance_schema_digest_lost"`
	SchemaRwlockInstancesLost uint64 `json:"performance_schema_rwlock_instances_lost"`
	SchemaThreadInstancesLost uint64 `json:"performance_schema_thread_instances_lost"`
	SchemaTableLockStatLost   uint64 `json:"performance_schema_table_lock_stat_lost"`

	// engines
	InnoDB *InnoDBMetric `json:"innodb"`
}

// MySQLMetric contains system and databases metrics
type MySQLMetric struct {
	SequenceID      uint64            `json:"sequence_id"`
	MachineID       string            `json:"machine_id"`
	MessageID       string            `json:"message_id"`
	ServiceID       string            `json:"service_id"`
	ReportTimestamp uint64            `json:"report_timestamp"`
	Host            *HostMetric       `json:"system"`
	Databases       []*DatabaseMetric `json:"databases"`
}
