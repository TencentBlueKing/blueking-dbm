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
	ServerCharset    string `json:"character_set_server"`

	// Performance Connection metric
	ThreadsRunning            int `json:"threads_running"`
	ConnectionsAborted        int `json:"aborted_connects"`
	Connections               int `json:"connections"`
	ConnectionsErrorsAccept   int `json:"connection_errors_accept"`
	ConnectionsErrorsInternal int `json:"connection_errors_internal"`
	ConnectionsErrorsPeerAddr int `json:"connection_errors_peer_address"`

	// MySQL Performance Query metric
	QueryTotal     uint64 `json:"queries"`
	AvgQPS         uint   `json:"avg_qps"`
	AvgTPS         uint   `json:"avg_tps"`
	QPS            uint   `json:"qps"`
	TPS            uint   `json:"tps"`
	QueryQuestions uint64 `json:"questions"`
	QuerySelects   uint64 `json:"com_select"`
	QueryInserts   uint64 `json:"com_insert"`
	QueryUpdates   uint64 `json:"com_update"`
	QueryDeletes   uint64 `json:"com_delete"`
	QuerySlow      uint64 `json:"slow_queries"`
	QueryCommits   uint64 `json:"query_commits"`
	QueryRollbacks uint64 `json:"query_rollbacks"`

	// MySQL Performance Query Cache metric
	KeyReadRequests   uint64  `json:"key_read_requests"`
	KeyReads          uint64  `json:"key_reads"`
	KeyBufferHitRate  float64 `json:"key_buffer_hit_rate"`
	QCacheHits        uint64  `json:"qcache_hits"`
	QCacheFreeBlocks  uint64  `json:"qcache_free_blocks"`
	QCacheFreeMem     uint64  `json:"qcache_free_mem"`
	QCacheInserts     uint64  `json:"qcache_inserts"`
	QCachePrunes      uint64  `json:"qcache_lowmen_prunes"`
	QCacheNotCached   uint64  `json:"qcache_not_cached"`
	QCacheTotalBlocks uint64  `json:"qcache_total_blocks"`

	// MySQL Performance InnoDB handler metrics
	HandlerReadKey      uint64 `json:"handler_read_key"`
	HandlerReadRndNext  uint64 `json:"handler_read_rnd_next"`
	HandlerWrite        uint64 `json:"handler_write"`
	HandlerPrepare      int64  `json:"handler_prepare"`
	HandlerCommit       uint64 `json:"handler_commit"`
	HandlerExternalLock uint64 `json:"handler_external_lock"`

	// Performance Table statistical metrics
	TableCreatedTmp     uint64 `json:"created_tmp_tables"`
	TableCreatedTmpDisk uint64 `json:"created_tmp_disk_tables"`
	FileCreatedTmp      uint64 `json:"created_tmp_files"`
	FileOpen            uint64 `json:"opened_files"`
	TableOpen           uint64 `json:"opened_tables"`
	TableFlush          uint   `json:"flush_commands"`

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
