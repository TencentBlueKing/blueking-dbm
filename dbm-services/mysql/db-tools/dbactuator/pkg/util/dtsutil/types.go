/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package dtsutil 提供 MySQL DTS Master OpenAPI 客户端、任务状态/位点判定、sync_scope 展开与源端表级读锁等公共操作。
// 本包不依赖组件层（pkg/components），也不依赖顶层 util 包，避免 import cycle。
package dtsutil

import (
	"database/sql"
	"time"

	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

const (
	// PacketMarginBytes 相对 max_allowed_packet 的安全余量（1MB）。
	PacketMarginBytes = 1024 * 1024
	// LockWaitTimeoutSec 会话级锁等待超时。
	LockWaitTimeoutSec = 5
)

const (
	// stopWhileLockedServerTimeout 持锁窗口内让 Master 放弃停止的上限。
	stopWhileLockedServerTimeout = 15 * time.Second
	// stopWhileLockedHTTPTimeout 略长于服务端，避免套接字比 Master 更晚放弃。
	stopWhileLockedHTTPTimeout = 20 * time.Second
)

// SyncStatus DTS 任务增量同步状态（HTTP status 子集）。
type SyncStatus struct {
	MasterBinlog        string   `json:"master_binlog"`
	MasterBinlogGtid    string   `json:"master_binlog_gtid"`
	SyncerBinlog        string   `json:"syncer_binlog"`
	SyncerBinlogGtid    string   `json:"syncer_binlog_gtid"`
	BlockingDDLs        []string `json:"blocking_ddls"`
	SecondsBehindMaster int      `json:"seconds_behind_master"`
	Synced              bool     `json:"synced"`
}

// TaskStage worker 子任务阶段。出错时为 Paused，错误原文在 error_msg。
type TaskStage string

const (
	TaskStageNew          TaskStage = "New"
	TaskStageRunning      TaskStage = "Running"
	TaskStagePausing      TaskStage = "Pausing"
	TaskStagePaused       TaskStage = "Paused"
	TaskStageResuming     TaskStage = "Resuming"
	TaskStageStopping     TaskStage = "Stopping"
	TaskStageStopped      TaskStage = "Stopped"
	TaskStageFinished     TaskStage = "Finished"
	TaskStageInvalidStage TaskStage = "InvalidStage"
)

// TaskStatusItem GET /api/v1/tasks/{task}/status 单条。
type TaskStatusItem struct {
	Name       string      `json:"name"`
	SourceName string      `json:"source_name"`
	Stage      TaskStage   `json:"stage"`
	Unit       string      `json:"unit"`
	ErrorMsg   string      `json:"error_msg"`
	SyncStatus *SyncStatus `json:"sync_status"`
}

// TaskStatusListResponse 任务状态列表响应。
type TaskStatusListResponse struct {
	Total int              `json:"total"`
	Data  []TaskStatusItem `json:"data"`
}

// CutoverPositionOutput 供 Flow 落库的位点输出。
type CutoverPositionOutput struct {
	TaskName  string                   `json:"task_name"`
	Sources   []SourcePositionSnapshot `json:"sources"`
	StoppedAt string                   `json:"stopped_at"`
}

// SourcePositionSnapshot 单个 source 的位点快照。
type SourcePositionSnapshot struct {
	SourceName       string `json:"source_name"`
	MasterBinlog     string `json:"master_binlog"`
	MasterBinlogGtid string `json:"master_binlog_gtid"`
	SyncerBinlog     string `json:"syncer_binlog"`
	SyncerBinlogGtid string `json:"syncer_binlog_gtid"`
	SecondsBehind    int    `json:"seconds_behind_master"`
}

// BinlogCoord DTS sync_status 位点解析结果。
// 示例输入："(binlog20000.002894, 12105)" → File=binlog20000.002894, Position=12105
type BinlogCoord struct {
	File     string
	Position int64
}

// Endpoint 源端连接信息（临时账号；连接发起方 = dts-master）。
type Endpoint struct {
	Host       string     `json:"host" validate:"required"`
	Port       int        `json:"port" validate:"required,gt=0"`
	User       string     `json:"user" validate:"required"`
	Password   string     `json:"password" validate:"required"`
	SourceName string     `json:"source_name"`
	SyncScope  *SyncScope `json:"sync_scope"`
}

// StopTaskRequest POST /api/v1/tasks/{task}/stop 请求体（与 OpenAPI 对齐）。
type StopTaskRequest struct {
	SourceNameList  []string `json:"source_name_list,omitempty"`
	TimeoutDuration string   `json:"timeout_duration,omitempty"`
}

// SyncScope 紧凑同步范围（与 DTS table_filter / Flow sync_scope 同形）。
type SyncScope struct {
	DoDBs         []string     `json:"do_dbs"`
	IgnoreDBs     []string     `json:"ignore_dbs"`
	DoTables      []TableItem  `json:"do_tables"`
	IgnoreTables  []TableItem  `json:"ignore_tables"`
	TableRoutes   []TableRoute `json:"table_routes"`
	BinlogFilters []any        `json:"binlog_filters"` // 加锁不消费；保留透传
}

// TableRoute 对应 Flow sync_scope.table_routes / DTS routes（库表映射）。
// 加锁只看源端匹配；target_* 仅透传，不参与 Expand。
type TableRoute struct {
	SourceName         string `json:"source_name,omitempty"`
	SourceDB           string `json:"source_db,omitempty"`
	SourceDBPattern    string `json:"source_db_pattern,omitempty"`
	SourceTable        string `json:"source_table,omitempty"`
	SourceTablePattern string `json:"source_table_pattern,omitempty"`
	TargetDB           string `json:"target_db,omitempty"`
	TargetTable        string `json:"target_table,omitempty"`
}

// TableItem 表引用；兼容 dict({db|schema,table}) 或 "db.table" 字符串。
type TableItem struct {
	Schema string `json:"schema"`
	Table  string `json:"table"`
}

// LockedTable 待加锁的具体表。
type LockedTable struct {
	Schema string
	Table  string
}

// SourceLockConn 单个源端持锁连接。
type SourceLockConn struct {
	Endpoint Endpoint
	Worker   *native.DbWorker
	LockConn *sql.Conn
	Tables   []LockedTable
}

// StatusSourceKey 取 status item 的 source 键（优先 source_name）。
func StatusSourceKey(item TaskStatusItem) string {
	if item.SourceName != "" {
		return item.SourceName
	}
	return item.Name
}
