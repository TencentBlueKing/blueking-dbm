/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package dtsutil

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"path"
	"slices"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/mysqlcomm"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

// IsEmpty 是否无任何可展开规则。
func (s *SyncScope) IsEmpty() bool {
	if s == nil {
		return true
	}
	if len(s.TableRoutes) > 0 {
		return false
	}
	return len(s.DoDBs) == 0 || len(s.DoTables) == 0
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

// ExpandSyncScope 在源端按 sync_scope 展开具体表清单。
// 同名：先按 do_dbs 减 ignore_dbs 列出库，再按 do_tables 减 ignore_tables 列表。
// 重名：table_routes 具体表直接用，通配查 information_schema。空结果失败。
func ExpandSyncScope(db *sql.DB, scope *SyncScope) ([]LockedTable, error) {
	if scope == nil || scope.IsEmpty() {
		return nil, fmt.Errorf("sync_scope 为空，拒绝展开")
	}

	seen := make(map[string]struct{})
	var tables []LockedTable

	add := func(schema, table string) {
		if schema == "" || table == "" || table == "*" {
			return
		}
		if matchAnyBackupGlob(schema, scope.IgnoreDBs) {
			return
		}
		if matchIgnoreTable(schema, table, scope.IgnoreTables) {
			return
		}
		k := tableKey(schema, table)
		if _, ok := seen[k]; ok {
			return
		}
		seen[k] = struct{}{}
		tables = append(tables, LockedTable{Schema: schema, Table: table})
	}

	if len(scope.TableRoutes) > 0 {
		for _, route := range scope.TableRoutes {
			if err := expandTableRoute(db, route, add); err != nil {
				return nil, err
			}
		}
	} else if err := expandFourColumn(db, scope, add); err != nil {
		return nil, err
	}

	if len(tables) == 0 {
		return nil, fmt.Errorf("sync_scope 展开结果为空，拒绝空清单加锁")
	}
	logger.Info("展开待锁表数量 tables=%d", len(tables))
	return tables, nil
}

func expandFourColumn(db *sql.DB, scope *SyncScope, add func(schema, table string)) error {
	if err := rejectRegexInFourColumn(scope); err != nil {
		return err
	}
	schemas, err := resolveSchemasByBackupPatterns(db, scope.DoDBs)
	if err != nil {
		return err
	}
	tablePats := make([]string, 0, len(scope.DoTables))
	for _, it := range scope.DoTables {
		tablePats = append(tablePats, strings.TrimSpace(it.Table))
	}
	for _, schema := range schemas {
		if matchAnyBackupGlob(schema, scope.IgnoreDBs) {
			continue
		}
		if err := expandTablesByBackupPatterns(db, schema, tablePats, add); err != nil {
			return err
		}
	}
	return nil
}

func resolveSchemasByBackupPatterns(db *sql.DB, patterns []string) ([]string, error) {
	seen := map[string]struct{}{}
	var out []string
	for _, pat := range patterns {
		pat = strings.TrimSpace(pat)
		if pat == "" {
			continue
		}
		names, err := expandBackupSchemaPattern(db, pat)
		if err != nil {
			return nil, err
		}
		for _, name := range names {
			if !keepExpandedSchema(name, patterns) {
				continue
			}
			if _, ok := seen[name]; ok {
				continue
			}
			seen[name] = struct{}{}
			out = append(out, name)
		}
	}
	return out, nil
}

func expandBackupSchemaPattern(db *sql.DB, pat string) ([]string, error) {
	if isRegexPattern(pat) {
		return nil, fmt.Errorf("sync_scope 四列暂不支持正则(~) do_dbs=%q，请改用 %%/?/* 通配", pat)
	}
	if pat == "*" {
		return listSchemasLike(db, "%")
	}
	if hasBackupGlob(pat) {
		return listSchemasLike(db, backupGlobToSQLLike(pat))
	}
	return []string{pat}, nil
}

func expandTablesByBackupPatterns(db *sql.DB, schema string, patterns []string, add func(schema, table string)) error {
	for _, pat := range patterns {
		pat = strings.TrimSpace(pat)
		if pat == "" {
			continue
		}
		if pat == "*" {
			expanded, err := listBaseTables(db, schema)
			if err != nil {
				return err
			}
			for _, t := range expanded {
				add(t.Schema, t.Table)
			}
			continue
		}
		if hasBackupGlob(pat) {
			expanded, err := listBaseTablesLike(db, schema, backupGlobToSQLLike(pat))
			if err != nil {
				return err
			}
			for _, t := range expanded {
				add(t.Schema, t.Table)
			}
			continue
		}
		add(schema, pat)
	}
	return nil
}

func hasBackupGlob(pat string) bool {
	return strings.ContainsAny(pat, "*%?")
}

func backupGlobToSQLLike(pat string) string {
	var b strings.Builder
	for _, r := range pat {
		switch r {
		case '_':
			b.WriteString(`\_`)
		case '*', '%':
			b.WriteByte('%')
		case '?':
			b.WriteByte('_')
		default:
			b.WriteRune(r)
		}
	}
	return b.String()
}

func matchAnyBackupGlob(name string, pats []string) bool {
	for _, p := range pats {
		if matchBackupGlob(p, name) {
			return true
		}
	}
	return false
}

func matchIgnoreTable(schema, table string, items []TableItem) bool {
	for _, it := range items {
		sch := strings.TrimSpace(it.Schema)
		if sch == "" {
			sch = "*"
		}
		if !matchBackupGlob(sch, schema) {
			continue
		}
		if matchBackupGlob(strings.TrimSpace(it.Table), table) {
			return true
		}
	}
	return false
}

func matchBackupGlob(pat, name string) bool {
	p := strings.TrimSpace(pat)
	n := strings.TrimSpace(name)
	if p == "" {
		return false
	}
	if p == "*" {
		return true
	}
	var b strings.Builder
	for _, r := range p {
		switch r {
		case '*', '%':
			b.WriteByte('*')
		case '?':
			b.WriteByte('?')
		default:
			b.WriteRune(r)
		}
	}
	ok, err := path.Match(b.String(), n)
	return err == nil && ok
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

// keepExpandedSchema 丢掉展开命中的系统库（native.DBSys 与 backend.flow.consts.SYSTEM_DBS 同组），
// 仅当白名单精确写了 test 时保留 test。
func keepExpandedSchema(name string, patterns []string) bool {
	if !slices.Contains(native.DBSys, name) {
		return true
	}
	if name != native.TEST_DB {
		return false
	}
	for _, p := range patterns {
		if strings.TrimSpace(p) == native.TEST_DB {
			return true
		}
	}
	return false
}

func rejectRegexInFourColumn(scope *SyncScope) error {
	check := func(pats []string, field string) error {
		for _, p := range pats {
			if isRegexPattern(p) {
				return fmt.Errorf("sync_scope 四列暂不支持正则(~) %s=%q，请改用 %%/?/* 通配", field, p)
			}
		}
		return nil
	}
	if err := check(scope.DoDBs, "do_dbs"); err != nil {
		return err
	}
	if err := check(scope.IgnoreDBs, "ignore_dbs"); err != nil {
		return err
	}
	tablePats := make([]string, 0, len(scope.DoTables)+len(scope.IgnoreTables))
	for _, it := range scope.DoTables {
		if isRegexPattern(it.Schema) {
			return fmt.Errorf("sync_scope 四列暂不支持正则(~) do_tables.schema=%q", it.Schema)
		}
		tablePats = append(tablePats, it.Table)
	}
	for _, it := range scope.IgnoreTables {
		if isRegexPattern(it.Schema) {
			return fmt.Errorf("sync_scope 四列暂不支持正则(~) ignore_tables.schema=%q", it.Schema)
		}
		tablePats = append(tablePats, it.Table)
	}
	return check(tablePats, "tables")
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
	sysDBs, err := mysqlcomm.UnsafeBuilderStringIn(native.DBSys, "'")
	if err != nil {
		return nil, fmt.Errorf("构造系统库排除列表失败: %w", err)
	}
	q := fmt.Sprintf(`
SELECT SCHEMA_NAME
FROM information_schema.SCHEMATA
WHERE SCHEMA_NAME LIKE ? ESCAPE '\\'
  AND SCHEMA_NAME NOT IN (%s)`, sysDBs)
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

func tableKey(schema, table string) string {
	return schema + "." + table
}
