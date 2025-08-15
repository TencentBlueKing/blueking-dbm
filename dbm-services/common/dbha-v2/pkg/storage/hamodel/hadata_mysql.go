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

package hamodel

import (
	"strconv"
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

const (
	DatabaseName = "dbha_data"
)

// HostMetric host metric
type HostMetric struct {
	// Keys
	MachineID string `gorm:"column:machine_id;primaryKey"`

	// CPU
	CPUUsagePercent  float64 `gorm:"column:cpu_usage_percent"`
	CPUUserPercent   float64 `gorm:"column:cpu_user_percent"`
	CPUSystemPercent float64 `gorm:"column:cpu_system_percent"`
	CPUIOWaitPercent float64 `gorm:"column:cpu_iowait_percent"`
	CPULoad1         float64 `gorm:"column:cpu_load_1"`
	CPULoad5         float64 `gorm:"column:cpu_load_5"`
	CPULoad15        float64 `gorm:"column:cpu_load_15"`

	// Mem
	MemTotalMB     uint64 `gorm:"column:mem_total_mb"`
	MemUsedMB      uint64 `gorm:"column:mem_used_mb"`
	MemFreeMB      uint64 `gorm:"column:mem_free_mb"`
	MemCacheMB     uint64 `gorm:"column:mem_cache_mb"`
	MemAvailableMB uint64 `gorm:"column:mem_available_mb"`
	SwapTotalMB    uint64 `gorm:"column:swap_total_mb"`
	SwapUsedMB     uint64 `gorm:"column:swap_used_mb"`

	// Disk
	DiskUsagePercent float64 `gorm:"column:disk_usage_percent"`
	DiskTotal        uint64  `gorm:"column:disk_total"`
	DiskUsed         uint64  `gorm:"column:disk_used"`
	DiskAvailable    uint64  `gorm:"column:disk_available"`
	DiskReadOnly     bool    `gorm:"column:disk_read_only"`

	// Time automatically managed by GORM
	CreatedAt time.Time `gorm:"column:created_at;autoCreateTime"`
	UpdatedAt time.Time `gorm:"column:updated_at;autoUpdateTime"`
	DeletedAt time.Time `gorm:"column:deleted_at;"`
}

func (t HostMetric) TableName() string {
	return "t_host_metric"
}

// DatabaseMetric Databases metric
type DatabaseMetric struct {
	// Keys
	MachineID  string `gorm:"column:machine_id;primaryKey"`
	InstanceID string `gorm:"column:instance_id;primaryKey"`

	// Status
	Version          string  `gorm:"column:mysql_version"`
	ThreadsConnected uint    `gorm:"column:mysql_threads_connected"`
	ServerCharset    string  `gorm:"column:mysql_server_charset"`
	OpenTablesTotal  uint    `gorm:"column:mysql_open_tables_total"`
	FlushTables      uint    `gorm:"column:mysql_flush_tables"`
	OpenTablesNow    uint    `gorm:"column:mysql_open_tables_now"`
	SlowQueriesNow   uint    `gorm:"column:mysql_slow_queries_now"`
	TotalQuestions   uint    `gorm:"column:mysql_total_questions"`
	QueriesPerSecond float64 `gorm:"column:mysql_avg_qps"`

	// Performance Connection metric
	ThreadsRunning            int `gorm:"column:mysql_threads_running"`
	ConnectionsAborted        int `gorm:"column:mysql_connections_aborted"`
	Connections               int `gorm:"column:mysql_connections"`
	ConnectionsErrorsAccept   int `gorm:"column:mysql_connections_errors_accept"`
	ConnectionsErrorsInternal int `gorm:"column:mysql_connections_errors_internal"`
	ConnectionsErrorsPeerAddr int `gorm:"column:mysql_connections_errors_peer_address"`

	// MySQL Performance Query metric
	QueryTotal     uint64 `gorm:"column:mysql_quey_total"`
	QPS            uint   `gorm:"column:mysql_QPS"`
	TPS            uint   `gorm:"column:mysql_TPS"`
	QueryQuestions uint64 `grom:"column:mysql_questions_total"`
	QuerySelects   uint64 `gorm:"column:mysql_selects_times"`
	QueryInserts   uint64 `gorm:"column:mysql_inserts_times"`
	QueryUpdates   uint64 `gorm:"column:mysql_updates_times"`
	QueryDeletes   uint64 `gorm:"column:mysql_deletes_times"`
	QuerySlow      uint64 `gorm:"column:mysql_slow_queries_times"`

	// MySQL Performance Query Cache metric
	KeyReadRequests   uint64  `gorm:"column:key_read_requests"`
	KeyReads          uint64  `gorm:"column:key_reads"`
	KeyBufferHitRate  float64 `gorm:"column:key_buffer_hit_rate"`
	QCacheHits        uint64  `gorm:"column:query_cache_hits"`
	QCacheFreeBlocks  uint64  `gorm:"column:query_cache_free_blocks"`
	QCacheFreeMem     uint64  `gorm:"column:query_cache_free_mem"`
	QCacheInserts     uint64  `gorm:"column:query_cache_inserts"`
	QCachePrunes      uint64  `gorm:"column:query_cache_lowmen_prunes"`
	QCacheNotCached   uint64  `gorm:"column:query_cache_not_cached"`
	QCacheTotalBlocks uint64  `gorm:"column:query_cache_total_blocks"`

	// MySQL Performance InnoDB handler metrics
	HandlerReadKey      uint64 `gorm:"column:handler_read_key"`
	HandlerReadRndNext  uint64 `gorm:"column:handler_read_rnd_next"`
	HandlerWrite        uint64 `gorm:"column:handler_write"`
	HandlerPrepare      int64  `gorm:"column:handler_prepare"`
	HandlerCommit       uint64 `gorm:"column:handler_commit"`
	HandlerExternalLock uint64 `gorm:"column:handler_external_lock"`

	// Performance Table statistical metrics
	TableCreatedTmp     uint64 `gorm:"column:tables_created_tmp"`
	TableCreatedTmpDisk uint64 `gorm:"column:tables_created_tmp_disk"`
	FileCreatedTmp      uint64 `gorm:"column:files_created_tmp"`
	FileOpen            uint64 `gorm:"column:files_opened"`
	TableOpen           uint64 `gorm:"column:tables_opened"`

	// Performance BinLog metrics
	BinlogCacheDiskUse     uint64 `gorm:"column:binlog_cache_disk_use"`
	BinlogCacheUse         uint64 `gorm:"column:binlog_cache_use"`
	BinlogStmtCacheDiskUse uint64 `gorm:"column:binlog_stmt_cache_disk_use"`
	BinlogStmtCacheUse     uint64 `gorm:"column:binlog_stmt_cache_use"`

	// Performance Performance schema metrics
	SchemaAccountsLost        uint64 `gorm:"column:performance_schema_accounts_lost"`
	SchemaCondClassesLost     uint64 `gorm:"column:performance_schema_cond_classes_lost"`
	SchemaFileHandlesLost     uint64 `gorm:"column:performance_schema_file_handles_lost"`
	SchemaLockerLost          uint64 `gorm:"column:performance_schema_locker_lost"`
	SchemaDigestLost          uint64 `gorm:"column:performance_schema_digest_lost"`
	SchemaRwlockInstancesLost uint64 `gorm:"column:performance_schema_rwlock_instances_lost"`
	SchemaThreadInstancesLost uint64 `gorm:"column:performance_schema_thread_instances_lost"`
	SchemaTableLockStatLost   uint64 `gorm:"column:performance_schema_table_lock_stat_lost"`

	// Time automatically managed by GORM
	CreatedAt time.Time `gorm:"column:created_at;autoCreateTime"`
	UpdatedAt time.Time `gorm:"column:updated_at;autoUpdateTime"`
	DeletedAt time.Time `gorm:"column:deleted_at"`
}

func (t DatabaseMetric) TableName() string {
	return "t_mysql_metric"
}

// DBHAMySQL contains system and databases metrics
type DBHAMySQL struct {
	MachineID       string `gorm:"column:machine_id;primaryKey"`
	SequenceID      uint64 `gorm:"column:sequence_id"`
	MessageID       string `gorm:"column:message_id"`
	ServiceID       string `gorm:"column:service_id"`
	ReportTimestamp uint64 `gorm:"column:report_timestamp"`

	Host      *HostMetric       `gorm:"foreignKey:machine_id;references:machine_id"`
	Events    []*MySQLEvent     `gorm:"foreignKey:machine_id;references:machine_id"`
	Databases []*DatabaseMetric `gorm:"foreignKey:machine_id;references:machine_id"`

	// Time automatically managed by GORM
	CreatedAt time.Time `gorm:"column:created_at;autoCreateTime"`
	UpdatedAt time.Time `gorm:"column:updated_at;autoUpdateTime"`
	DeletedAt time.Time `gorm:"column:deleted_at"`
}

func NewDBHAMySQL(msg *haprobe.MySQLMetric) *DBHAMySQL {
	data := &DBHAMySQL{}

	data.MachineID = msg.MachineID
	data.SequenceID = msg.SequenceID
	data.MessageID = msg.MessageID
	data.ServiceID = msg.ServiceID
	data.ReportTimestamp = msg.ReportTimestamp

	data.Host = &HostMetric{
		MachineID: msg.MachineID,

		CPUUsagePercent:  msg.Host.CPUUsagePercent,
		CPUUserPercent:   msg.Host.CPUUserPercent,
		CPUSystemPercent: msg.Host.CPUSystemPercent,
		CPUIOWaitPercent: msg.Host.CPUIOWaitPercent,
		CPULoad1:         msg.Host.CPULoad1,
		CPULoad5:         msg.Host.CPULoad5,
		CPULoad15:        msg.Host.CPULoad15,

		MemTotalMB:     msg.Host.MemTotalMB,
		MemUsedMB:      msg.Host.MemUsedMB,
		MemFreeMB:      msg.Host.MemFreeMB,
		MemCacheMB:     msg.Host.MemCacheMB,
		MemAvailableMB: msg.Host.MemAvailableMB,
		SwapTotalMB:    msg.Host.SwapTotalMB,
		SwapUsedMB:     msg.Host.SwapUsedMB,

		DiskUsagePercent: msg.Host.DiskUsagePercent,
		DiskTotal:        msg.Host.DiskTotal,
		DiskUsed:         msg.Host.DiskUsed,
		DiskAvailable:    msg.Host.DiskAvailable,
		DiskReadOnly:     msg.Host.DiskReadOnly,
	}

	for _, event := range msg.Events {
		if event == nil {
			logger.Warn("skip this recored, event is nil, machine-id: %s", msg.MachineID)
			continue
		}

		data.Events = append(data.Events, &MySQLEvent{
			MachineID:  msg.MachineID,
			InstanceID: strconv.Itoa(event.Endpoint.Port),
			Type:       event.Type,
			Endpoint:   event.Endpoint.String(),
			Message:    event.Message,
		})
	}

	for _, db := range msg.Databases {
		if db == nil {
			logger.Warn("skip this record, db is nil, machine-id: %s", msg.MachineID)
			continue
		}
		data.loadDatabase(db)
	}

	return data
}

func (t DBHAMySQL) TableName() string {
	return "t_dbha_mysql"
}

func (t *DBHAMySQL) loadDatabase(db *haprobe.DatabaseMetric) {
	t.Databases = append(t.Databases, &DatabaseMetric{
		MachineID:  t.MachineID,
		InstanceID: strconv.Itoa(db.ListenPort),

		Version:          db.Version,
		ThreadsConnected: db.ThreadsConnected,
		ServerCharset:    db.ServerCharset,

		ThreadsRunning:            db.ThreadsRunning,
		ConnectionsAborted:        db.ConnectionsAborted,
		Connections:               db.Connections,
		ConnectionsErrorsAccept:   db.ConnectionsErrorsAccept,
		ConnectionsErrorsInternal: db.ConnectionsErrorsInternal,
		ConnectionsErrorsPeerAddr: db.ConnectionsErrorsPeerAddr,

		QueryTotal:     db.QueryTotal,
		QPS:            db.QPS,
		TPS:            db.TPS,
		QueryQuestions: db.QueryQuestions,
		QuerySelects:   db.QuerySelects,
		QueryInserts:   db.QueryInserts,
		QueryUpdates:   db.QueryUpdates,
		QueryDeletes:   db.QueryDeletes,
		QuerySlow:      db.QuerySlow,

		KeyReadRequests:   db.KeyReadRequests,
		KeyReads:          db.KeyReads,
		KeyBufferHitRate:  db.KeyBufferHitRate,
		QCacheHits:        db.QCacheHits,
		QCacheFreeBlocks:  db.QCacheFreeBlocks,
		QCacheFreeMem:     db.QCacheFreeMem,
		QCacheInserts:     db.QCacheInserts,
		QCachePrunes:      db.QCachePrunes,
		QCacheNotCached:   db.QCacheNotCached,
		QCacheTotalBlocks: db.QCacheTotalBlocks,

		HandlerReadKey:      db.HandlerReadKey,
		HandlerReadRndNext:  db.HandlerReadRndNext,
		HandlerWrite:        db.HandlerWrite,
		HandlerPrepare:      db.HandlerPrepare,
		HandlerCommit:       db.HandlerCommit,
		HandlerExternalLock: db.HandlerExternalLock,

		TableCreatedTmp:     db.TableCreatedTmp,
		TableCreatedTmpDisk: db.TableCreatedTmpDisk,
		FileCreatedTmp:      db.FileCreatedTmp,
		FileOpen:            db.FileOpen,
		TableOpen:           db.TableOpen,

		BinlogCacheDiskUse:     db.BinlogCacheUse,
		BinlogCacheUse:         db.BinlogCacheUse,
		BinlogStmtCacheDiskUse: db.BinlogStmtCacheDiskUse,
		BinlogStmtCacheUse:     db.BinlogStmtCacheUse,

		SchemaAccountsLost:        db.SchemaAccountsLost,
		SchemaCondClassesLost:     db.SchemaCondClassesLost,
		SchemaFileHandlesLost:     db.SchemaFileHandlesLost,
		SchemaLockerLost:          db.SchemaLockerLost,
		SchemaDigestLost:          db.SchemaDigestLost,
		SchemaRwlockInstancesLost: db.SchemaRwlockInstancesLost,
		SchemaThreadInstancesLost: db.SchemaThreadInstancesLost,
		SchemaTableLockStatLost:   db.SchemaTableLockStatLost,
	})

}
