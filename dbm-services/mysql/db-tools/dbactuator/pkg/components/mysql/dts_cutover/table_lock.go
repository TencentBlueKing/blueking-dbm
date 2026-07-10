/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package dts_cutover

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

const (
	// SoftTableLimit 展开后表数量软上限，便于早失败。
	SoftTableLimit = 2000
	// PacketMarginBytes 相对 max_allowed_packet 的安全余量（1MB）。
	PacketMarginBytes = 1024 * 1024
	// LockWaitTimeoutSec 会话级锁等待超时。
	LockWaitTimeoutSec = 10
)

// SyncScope 紧凑同步范围（与 Flow sync_scope 同形）。
type SyncScope struct {
	DoDBs         []string     `json:"do_dbs"`
	IgnoreDBs     []string     `json:"ignore_dbs"`
	DoTables      []TableItem  `json:"do_tables"`
	IgnoreTables  []TableItem  `json:"ignore_tables"`
	TableRoutes   []TableRoute `json:"table_routes"`
	BinlogFilters []any        `json:"binlog_filters"` // 加锁不消费；保留透传
}

// IsEmpty 是否无任何可展开规则。
func (s *SyncScope) IsEmpty() bool {
	if s == nil {
		return true
	}
	return len(s.DoDBs) == 0 && len(s.DoTables) == 0 && len(s.TableRoutes) == 0
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

// SourceSchema 源库匹配：pattern 优先于精确名（与 migrate_helper 一致）。
func (r TableRoute) SourceSchema() string {
	if s := strings.TrimSpace(r.SourceDBPattern); s != "" {
		return s
	}
	return strings.TrimSpace(r.SourceDB)
}

// SourceTableName 源表匹配：pattern 优先于精确名。
func (r TableRoute) SourceTableName() string {
	if s := strings.TrimSpace(r.SourceTablePattern); s != "" {
		return s
	}
	s := strings.TrimSpace(r.SourceTable)
	if s == "" {
		return "*"
	}
	return s
}

// TableItem 表引用；兼容 dict({db|schema,table}) 或 "db.table" 字符串。
type TableItem struct {
	Schema string `json:"schema"`
	Table  string `json:"table"`
}

// UnmarshalJSON 兼容多种表项形态。
func (t *TableItem) UnmarshalJSON(data []byte) error {
	var s string
	if err := json.Unmarshal(data, &s); err == nil {
		s = strings.TrimSpace(s)
		if s == "" {
			return fmt.Errorf("empty table item")
		}
		if i := strings.Index(s, "."); i >= 0 {
			t.Schema = s[:i]
			t.Table = s[i+1:]
		} else {
			t.Schema = "*"
			t.Table = s
		}
		return nil
	}
	var m map[string]any
	if err := json.Unmarshal(data, &m); err != nil {
		return err
	}
	t.Schema = firstString(m, "schema", "db", "dbname")
	t.Table = firstString(m, "table", "tablename")
	if t.Schema == "" {
		t.Schema = "*"
	}
	if t.Table == "" {
		t.Table = "*"
	}
	return nil
}

func firstString(m map[string]any, keys ...string) string {
	for _, k := range keys {
		if v, ok := m[k]; ok && v != nil {
			if s, ok := v.(string); ok && s != "" {
				return s
			}
		}
	}
	return ""
}

// LockedTable 待加锁的具体表。
type LockedTable struct {
	Schema string
	Table  string
}

// SourceLockConn 单个源端持锁连接。
type SourceLockConn struct {
	Endpoint SourceEndpoint
	Worker   *native.DbWorker
	LockConn *sql.Conn
	Tables   []LockedTable
}

// Close 关闭连接（unlock 应由调用方先执行）。
func (s *SourceLockConn) Close() {
	if s.LockConn != nil {
		_ = s.LockConn.Close()
		s.LockConn = nil
	}
	if s.Worker != nil {
		s.Worker.Close()
		s.Worker = nil
	}
}

// ExpandSyncScope 在源端按 sync_scope 展开具体表清单。
// 规则：do_tables / table_routes 具体表直接用；do_dbs / table=* / 通配符查 information_schema；应用 ignore_*；空结果失败。
func ExpandSyncScope(db *sql.DB, scope *SyncScope) ([]LockedTable, error) {
	if scope == nil || scope.IsEmpty() {
		return nil, fmt.Errorf("sync_scope 为空，拒绝展开")
	}
	ignoreDB := toSet(scope.IgnoreDBs)
	ignoreTable := make(map[string]struct{})
	for _, it := range scope.IgnoreTables {
		ignoreTable[tableKey(it.Schema, it.Table)] = struct{}{}
	}

	seen := make(map[string]struct{})
	var tables []LockedTable

	add := func(schema, table string) {
		if schema == "" || table == "" || table == "*" {
			return
		}
		if _, ok := ignoreDB[schema]; ok {
			return
		}
		if _, ok := ignoreTable[tableKey(schema, table)]; ok {
			return
		}
		if _, ok := ignoreTable[tableKey(schema, "*")]; ok {
			return
		}
		if _, ok := ignoreTable[tableKey("*", "*")]; ok {
			return
		}
		k := tableKey(schema, table)
		if _, ok := seen[k]; ok {
			return
		}
		seen[k] = struct{}{}
		tables = append(tables, LockedTable{Schema: schema, Table: table})
	}

	// do_dbs → 库内全部 BASE TABLE
	for _, dbName := range scope.DoDBs {
		if dbName == "" {
			continue
		}
		if _, ok := ignoreDB[dbName]; ok {
			continue
		}
		expanded, err := listBaseTables(db, dbName)
		if err != nil {
			return nil, err
		}
		for _, t := range expanded {
			add(t.Schema, t.Table)
		}
	}

	// do_tables
	for _, it := range scope.DoTables {
		schema, table := it.Schema, it.Table
		if schema == "" {
			schema = "*"
		}
		if table == "" {
			table = "*"
		}
		if _, ok := ignoreDB[schema]; ok {
			continue
		}
		if table == "*" {
			if schema == "*" || schema == "" {
				return nil, fmt.Errorf("do_tables 含 schema=* 且 table=*，拒绝全实例展开（禁止裸 FTWRL）")
			}
			expanded, err := listBaseTables(db, schema)
			if err != nil {
				return nil, err
			}
			for _, t := range expanded {
				add(t.Schema, t.Table)
			}
			continue
		}
		add(schema, table)
	}

	// table_routes → 源端库表（与 DTS routes / table_migrate_rule 同形）
	for _, route := range scope.TableRoutes {
		if err := expandTableRoute(db, route, add); err != nil {
			return nil, err
		}
	}

	if len(tables) == 0 {
		return nil, fmt.Errorf("sync_scope 展开结果为空，拒绝空清单加锁")
	}
	if len(tables) > SoftTableLimit {
		return nil, fmt.Errorf(
			"展开表数量 %d 超过软上限 %d，请缩小迁移范围",
			len(tables), SoftTableLimit,
		)
	}
	return tables, nil
}

// expandTableRoute 将单条 table_route 展开为源端具体表；add 负责去重与 ignore。
func expandTableRoute(db *sql.DB, route TableRoute, add func(schema, table string)) error {
	schemaPat := route.SourceSchema()
	tablePat := route.SourceTableName()
	if schemaPat == "" {
		return fmt.Errorf("table_routes 条目缺少 source_db/source_db_pattern")
	}
	if isRegexPattern(schemaPat) || isRegexPattern(tablePat) {
		return fmt.Errorf(
			"table_routes 暂不支持正则(~) 模式 schema=%q table=%q，请改为 * 通配或具体名",
			schemaPat, tablePat,
		)
	}
	if (schemaPat == "*" || schemaPat == "") && tablePat == "*" {
		return fmt.Errorf("table_routes 含 schema=* 且 table=*，拒绝全实例展开（禁止裸 FTWRL）")
	}

	schemas, err := resolveSchemaNames(db, schemaPat)
	if err != nil {
		return err
	}
	for _, schema := range schemas {
		if tablePat == "*" {
			expanded, err := listBaseTables(db, schema)
			if err != nil {
				return err
			}
			for _, t := range expanded {
				add(t.Schema, t.Table)
			}
			continue
		}
		if hasGlobMeta(tablePat) {
			expanded, err := listBaseTablesLike(db, schema, globToSQLLike(tablePat))
			if err != nil {
				return err
			}
			for _, t := range expanded {
				add(t.Schema, t.Table)
			}
			continue
		}
		add(schema, tablePat)
	}
	return nil
}

func isRegexPattern(pat string) bool {
	return strings.HasPrefix(strings.TrimSpace(pat), "~")
}

func hasGlobMeta(pat string) bool {
	return strings.Contains(pat, "*")
}

// globToSQLLike 将简单 * 通配转为 LIKE（并转义 %/_）。
func globToSQLLike(pat string) string {
	var b strings.Builder
	for _, r := range pat {
		switch r {
		case '%', '_':
			b.WriteByte('\\')
			b.WriteRune(r)
		case '*':
			b.WriteByte('%')
		default:
			b.WriteRune(r)
		}
	}
	return b.String()
}

func resolveSchemaNames(db *sql.DB, schemaPat string) ([]string, error) {
	if schemaPat == "*" {
		return nil, fmt.Errorf("table_routes 不支持 schema=*，请指定库名或带 * 的库前缀模式")
	}
	if !hasGlobMeta(schemaPat) {
		return []string{schemaPat}, nil
	}
	return listSchemasLike(db, globToSQLLike(schemaPat))
}

func listSchemasLike(db *sql.DB, likePat string) ([]string, error) {
	const q = `
SELECT SCHEMA_NAME
FROM information_schema.SCHEMATA
WHERE SCHEMA_NAME LIKE ? ESCAPE '\\'`
	rows, err := db.Query(q, likePat)
	if err != nil {
		return nil, fmt.Errorf("查询 SCHEMATA LIKE %q 失败: %w", likePat, err)
	}
	defer rows.Close()
	var out []string
	for rows.Next() {
		var name string
		if err = rows.Scan(&name); err != nil {
			return nil, err
		}
		out = append(out, name)
	}
	return out, rows.Err()
}

func listBaseTables(db *sql.DB, schema string) ([]LockedTable, error) {
	const q = `
SELECT TABLE_SCHEMA, TABLE_NAME
FROM information_schema.TABLES
WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA = ?`
	rows, err := db.Query(q, schema)
	if err != nil {
		return nil, fmt.Errorf("查询 information_schema 失败 schema=%s: %w", schema, err)
	}
	defer rows.Close()
	var out []LockedTable
	for rows.Next() {
		var t LockedTable
		if err = rows.Scan(&t.Schema, &t.Table); err != nil {
			return nil, err
		}
		out = append(out, t)
	}
	return out, rows.Err()
}

func listBaseTablesLike(db *sql.DB, schema, tableLike string) ([]LockedTable, error) {
	const q = `
SELECT TABLE_SCHEMA, TABLE_NAME
FROM information_schema.TABLES
WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA = ? AND TABLE_NAME LIKE ? ESCAPE '\\'`
	rows, err := db.Query(q, schema, tableLike)
	if err != nil {
		return nil, fmt.Errorf("查询 information_schema LIKE 失败 schema=%s table~%s: %w", schema, tableLike, err)
	}
	defer rows.Close()
	var out []LockedTable
	for rows.Next() {
		var t LockedTable
		if err = rows.Scan(&t.Schema, &t.Table); err != nil {
			return nil, err
		}
		out = append(out, t)
	}
	return out, rows.Err()
}

func toSet(items []string) map[string]struct{} {
	m := make(map[string]struct{}, len(items))
	for _, it := range items {
		if it != "" {
			m[it] = struct{}{}
		}
	}
	return m
}

func tableKey(schema, table string) string {
	return schema + "." + table
}

// BuildFlushTablesReadLockSQL 构造单句 FLUSH TABLES t1,t2,... WITH READ LOCK（禁止裸 FTWRL / 假分批）。
func BuildFlushTablesReadLockSQL(tables []LockedTable) (string, error) {
	if len(tables) == 0 {
		return "", fmt.Errorf("加锁表清单为空，禁止执行裸 FLUSH TABLES WITH READ LOCK")
	}
	parts := make([]string, 0, len(tables))
	for _, t := range tables {
		parts = append(parts, fmt.Sprintf("%s.%s", quoteIdent(t.Schema), quoteIdent(t.Table)))
	}
	return "FLUSH TABLES " + strings.Join(parts, ",") + " WITH READ LOCK", nil
}

func quoteIdent(name string) string {
	return "`" + strings.ReplaceAll(name, "`", "``") + "`"
}

// ValidateFlushSQLBudget 校验语句长度相对 max_allowed_packet 的预算。
func ValidateFlushSQLBudget(flushSQL string, maxAllowedPacket int64) error {
	if maxAllowedPacket <= 0 {
		return fmt.Errorf("max_allowed_packet 无效: %d", maxAllowedPacket)
	}
	budget := maxAllowedPacket - PacketMarginBytes
	if budget <= 0 {
		return fmt.Errorf(
			"max_allowed_packet(%d) 过小，无法满足 margin=%d",
			maxAllowedPacket, PacketMarginBytes,
		)
	}
	n := int64(len([]byte(flushSQL)))
	if n >= budget {
		return fmt.Errorf(
			"FLUSH 语句长度 %d 字节超过预算 %d (max_allowed_packet=%d - margin=%d)；请缩小迁移范围或调大 max_allowed_packet；禁止假分批 FLUSH",
			n, budget, maxAllowedPacket, PacketMarginBytes,
		)
	}
	return nil
}

// LockSourceTables 连接源端、展开（或使用给定表）、单句表级 READ 锁。
func LockSourceTables(ep SourceEndpoint, scope *SyncScope, lockTables []TableItem) (*SourceLockConn, error) {
	inst := native.InsObject{
		Host: ep.Host,
		Port: ep.Port,
		User: ep.User,
		Pwd:  ep.Password,
	}
	worker, err := inst.Conn()
	if err != nil {
		return nil, fmt.Errorf(
			"连接源端 %s:%d 失败（请检查临时账号是否授权 dts-master IP）: %w",
			ep.Host, ep.Port, err,
		)
	}
	sl := &SourceLockConn{Endpoint: ep, Worker: worker}
	cleanupOnErr := true
	defer func() {
		if cleanupOnErr {
			sl.Close()
		}
	}()

	tables, err := resolveTablesList(worker.Db, scope, lockTables)
	if err != nil {
		return nil, err
	}
	sl.Tables = tables

	flushSQL, err := BuildFlushTablesReadLockSQL(tables)
	if err != nil {
		return nil, err
	}

	var maxAllowedPacket int64
	if err = worker.Db.QueryRow("SELECT @@max_allowed_packet").Scan(&maxAllowedPacket); err != nil {
		return nil, fmt.Errorf("读取 max_allowed_packet 失败: %w", err)
	}
	if err = ValidateFlushSQLBudget(flushSQL, maxAllowedPacket); err != nil {
		return nil, err
	}

	ctx := context.Background()
	lockConn, err := worker.Db.Conn(ctx)
	if err != nil {
		return nil, fmt.Errorf("获取持锁连接失败: %w", err)
	}
	sl.LockConn = lockConn

	if _, err = lockConn.ExecContext(ctx, fmt.Sprintf("SET lock_wait_timeout = %d", LockWaitTimeoutSec)); err != nil {
		return nil, fmt.Errorf("设置 lock_wait_timeout 失败: %w", err)
	}

	logger.Info(
		"源端 %s:%d 对 %d 张表执行单句 FLUSH TABLES ... WITH READ LOCK (sql_bytes=%d)",
		ep.Host, ep.Port, len(tables), len(flushSQL),
	)
	lockCtx, cancel := context.WithTimeout(ctx, time.Duration(LockWaitTimeoutSec+5)*time.Second)
	defer cancel()
	if _, err = lockConn.ExecContext(lockCtx, flushSQL); err != nil {
		return nil, fmt.Errorf("源端加表读锁失败 %s:%d: %w", ep.Host, ep.Port, err)
	}

	cleanupOnErr = false
	return sl, nil
}

// UnlockSource 释放表锁。
func UnlockSource(sl *SourceLockConn) error {
	if sl == nil || sl.LockConn == nil {
		return nil
	}
	_, err := sl.LockConn.ExecContext(context.Background(), "UNLOCK TABLES")
	if err != nil {
		logger.Error("源端 %s:%d UNLOCK TABLES 失败: %s", sl.Endpoint.Host, sl.Endpoint.Port, err.Error())
		return err
	}
	logger.Info("源端 %s:%d 已 UNLOCK TABLES", sl.Endpoint.Host, sl.Endpoint.Port)
	return nil
}
