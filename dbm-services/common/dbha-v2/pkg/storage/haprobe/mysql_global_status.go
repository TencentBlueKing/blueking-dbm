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

type MySqlGlobalStatus struct {
	ListenPort int `json:"listen_port,omitempty"`

	// Base Status
	Version                string `json:"mysql_version,omitempty"`
	Uptime                 uint64 `json:"uptime,omitempty"`
	UptimeSinceFlushStatus uint64 `json:"uptime_since_flush_status,omitempty"`
	ServerCharset          string `json:"character_set_server,omitempty"`
	OpenFiles              uint64 `json:"open_files,omitempty"`
	OpenTableDefinitions   int    `json:"open_table_definitions,omitempty"`
	OpenTables             uint64 `json:"open_tables,omitempty"`
	OpenedFiles            int    `json:"opened_files,omitempty"`
	OpenedTableDefinitions int    `json:"opened_table_definitions,omitempty"`
	OpenedTables           int    `json:"opened_tables,omitempty"`
	TableLocksImmediate    int    `json:"table_locks_immediate,omitempty"`
	TableLocksWaited       int    `json:"table_locks_waited,omitempty"`
	TableOpenCacheHits     int    `json:"table_open_cache_hits,omitempty"`
	TableOpenCacheMisses   int    `json:"table_open_cache_misses,omitempty"`

	// Control Center Status
	TcIsPrimary bool `json:"tc_is_primary,omitempty"`

	// Performance Connection metric
	ThreadsCached             int  `json:"threads_cached,omitempty"`
	ThreadsConnected          uint `json:"threads_connected,omitempty"`
	ThreadsCreated            int  `json:"threads_created,omitempty"`
	ThreadsRunning            int  `json:"threads_running,omitempty"`
	ConnectionsAborted        int  `json:"aborted_connects,omitempty"`
	Connections               int  `json:"connections,omitempty"`
	ConnectionsErrorsAccept   int  `json:"connection_errors_accept,omitempty"`
	ConnectionsErrorsInternal int  `json:"connection_errors_internal,omitempty"`
	ConnectionsErrorsPeerAddr int  `json:"connection_errors_peer_address,omitempty"`

	// MySQL Performance Query metric
	QueryTotal     uint64 `json:"queries,omitempty"`
	AvgQPS         uint   `json:"avg_qps,omitempty"`
	AvgTPS         uint   `json:"avg_tps,omitempty"`
	QPS            uint   `json:"qps,omitempty"`
	TPS            uint   `json:"tps,omitempty"`
	QueryQuestions uint64 `json:"questions,omitempty"`
	QuerySelects   uint64 `json:"com_select,omitempty"`
	QueryInserts   uint64 `json:"com_insert,omitempty"`
	QueryUpdates   uint64 `json:"com_update,omitempty"`
	QueryDeletes   uint64 `json:"com_delete,omitempty"`
	QuerySlow      uint64 `json:"slow_queries,omitempty"`
	QueryCommits   uint64 `json:"query_commits,omitempty"`
	QueryRollbacks uint64 `json:"query_rollbacks,omitempty"`

	// MySQL Performance Query Cache metric
	KeyReadRequests   uint64  `json:"key_read_requests,omitempty"`
	KeyReads          uint64  `json:"key_reads,omitempty"`
	KeyBufferHitRate  float64 `json:"key_buffer_hit_rate,omitempty"`
	QCacheHits        uint64  `json:"qcache_hits,omitempty"`
	QCacheFreeBlocks  uint64  `json:"qcache_free_blocks,omitempty"`
	QCacheFreeMem     uint64  `json:"qcache_free_mem,omitempty"`
	QCacheInserts     uint64  `json:"qcache_inserts,omitempty"`
	QCachePrunes      uint64  `json:"qcache_lowmen_prunes,omitempty"`
	QCacheNotCached   uint64  `json:"qcache_not_cached,omitempty"`
	QCacheTotalBlocks uint64  `json:"qcache_total_blocks,omitempty"`

	// MySQL Performance InnoDB handler metrics
	HandlerReadKey      uint64 `json:"handler_read_key,omitempty"`
	HandlerReadRndNext  uint64 `json:"handler_read_rnd_next,omitempty"`
	HandlerWrite        uint64 `json:"handler_write,omitempty"`
	HandlerPrepare      int64  `json:"handler_prepare,omitempty"`
	HandlerCommit       uint64 `json:"handler_commit,omitempty"`
	HandlerExternalLock uint64 `json:"handler_external_lock,omitempty"`

	// Performance Table statistical metrics
	TableCreatedTmp     uint64 `json:"created_tmp_tables,omitempty"`
	TableCreatedTmpDisk uint64 `json:"created_tmp_disk_tables,omitempty"`
	FileCreatedTmp      uint64 `json:"created_tmp_files,omitempty"`
	TableFlush          uint   `json:"flush_commands,omitempty"`

	// Performance BinLog metrics
	BinlogCacheDiskUse     uint64 `json:"binlog_cache_disk_use,omitempty"`
	BinlogCacheUse         uint64 `json:"binlog_cache_use,omitempty"`
	BinlogStmtCacheDiskUse uint64 `json:"binlog_stmt_cache_disk_use,omitempty"`
	BinlogStmtCacheUse     uint64 `json:"binlog_stmt_cache_use,omitempty"`

	// Performance Performance schema metrics
	SchemaAccountsLost        uint64 `json:"performance_schema_accounts_lost,omitempty"`
	SchemaCondClassesLost     uint64 `json:"performance_schema_cond_classes_lost,omitempty"`
	SchemaFileHandlesLost     uint64 `json:"performance_schema_file_handles_lost,omitempty"`
	SchemaLockerLost          uint64 `json:"performance_schema_locker_lost,omitempty"`
	SchemaDigestLost          uint64 `json:"performance_schema_digest_lost,omitempty"`
	SchemaRwlockInstancesLost uint64 `json:"performance_schema_rwlock_instances_lost,omitempty"`
	SchemaThreadInstancesLost uint64 `json:"performance_schema_thread_instances_lost,omitempty"`
	SchemaTableLockStatLost   uint64 `json:"performance_schema_table_lock_stat_lost,omitempty"`
}
