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

// DatabaseMetric Databases metric
type DatabaseMetric struct {
	ListenPort int `json:"listen_port"`

	// Status
	Version          string `json:"mysql_version"`
	ThreadsConnected uint   `json:"mysql_threads_connected"`
	ServerCharset    string `json:"mysql_server_charset"`

	// Performance Connection metric
	ThreadsRunning            int `json:"mysql_threads_running"`
	ConnectionsAborted        int `json:"mysql_connections_aborted"`
	Connections               int `json:"mysql_connections"`
	ConnectionsErrorsAccept   int `json:"mysql_connections_errors_accept"`
	ConnectionsErrorsInternal int `json:"mysql_connections_errors_internal"`
	ConnectionsErrorsPeerAddr int `json:"mysql_connections_errors_peer_address"`

	// MySQL Performance Query metric
	QueryTotal     uint64 `json:"mysql_quey_total"`
	AvgQPS         uint   `json:"mysql_avg_qps"`
	AvgTPS         uint   `json:"mysql_avg_tps"`
	QPS            uint   `json:"mysql_QPS"`
	TPS            uint   `json:"mysql_TPS"`
	QueryQuestions uint64 `json:"mysql_questions_total"`
	QuerySelects   uint64 `json:"mysql_selects_times"`
	QueryInserts   uint64 `json:"mysql_inserts_times"`
	QueryUpdates   uint64 `json:"mysql_updates_times"`
	QueryDeletes   uint64 `json:"mysql_deletes_times"`
	QuerySlow      uint64 `json:"mysql_slow_queries_times"`
	QueryCommits   uint64 `json:"mysql_commits_times"`
	QueryRollbacks uint64 `json:"mysql_rollbacks_times"`

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
	TableFlush          uint   `json:"tables_flushed"`

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
