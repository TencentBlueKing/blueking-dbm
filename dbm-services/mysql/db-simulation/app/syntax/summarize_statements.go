/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package syntax

import (
	"fmt"
	"regexp"

	"github.com/samber/lo"
)

// AlterTableRef 单条 ALTER TABLE 的表信息与原生 SQL
type AlterTableRef struct {
	DbName    string `json:"db_name"`
	TableName string `json:"table_name"`
	SqlText   string `json:"sql_text,omitempty"`
}

// AlterTableFileGroup 同一 SQL 文件内的 ALTER TABLE 列表
type AlterTableFileGroup struct {
	FileName string          `json:"file_name"`
	Alters   []AlterTableRef `json:"alters"`
}

// TableRef 库表名（不含原语句）
type TableRef struct {
	DbName    string `json:"db_name"`
	TableName string `json:"table_name"`
}

// TableFileGroup 同一 SQL 文件内的库表列表
type TableFileGroup struct {
	FileName string     `json:"file_name"`
	Tables   []TableRef `json:"tables"`
}

// SQLFileStatementSummary SQL 文件语句分析结果
type SQLFileStatementSummary struct {
	CommandCounts  map[string]int        `json:"command_counts"`
	AlterTables    []AlterTableFileGroup `json:"alter_tables"`
	DropTables     []TableFileGroup      `json:"drop_tables"`
	TruncateTables []TableFileGroup      `json:"truncate_tables"`
}

// qualifiedTableRe 匹配 `db` . `tbl` 或单独 `tbl`
var qualifiedTableRe = regexp.MustCompile("`([^`]+)`\\s*\\.\\s*`([^`]+)`|`([^`]+)`")

// SummarizeParsedStatements 按 command 全文件合计计数；
// ALTER TABLE 按文件返回表名，includeSQLText 为 true 时附带原语句；DROP/TRUNCATE 只返回表名。
func SummarizeParsedStatements(byFile map[string][]ParseIncludeTableBase, fileOrder []string, includeSQLText bool) (
	*SQLFileStatementSummary, error) {
	summary := &SQLFileStatementSummary{
		CommandCounts:  make(map[string]int),
		AlterTables:    make([]AlterTableFileGroup, 0),
		DropTables:     make([]TableFileGroup, 0),
		TruncateTables: make([]TableFileGroup, 0),
	}
	for _, fileName := range buildFileOrder(byFile, fileOrder) {
		fileSum, err := summarizeFileStatements(byFile[fileName], summary.CommandCounts, includeSQLText)
		if err != nil {
			return nil, err
		}
		appendFileGroups(summary, fileName, fileSum)
	}
	return summary, nil
}

type fileStatementSummary struct {
	alters    []AlterTableRef
	drops     []TableRef
	truncates []TableRef
}

func appendFileGroups(summary *SQLFileStatementSummary, fileName string, fileSum fileStatementSummary) {
	if len(fileSum.alters) > 0 {
		summary.AlterTables = append(summary.AlterTables, AlterTableFileGroup{
			FileName: fileName,
			Alters:   fileSum.alters,
		})
	}
	if len(fileSum.drops) > 0 {
		summary.DropTables = append(summary.DropTables, TableFileGroup{
			FileName: fileName,
			Tables:   fileSum.drops,
		})
	}
	if len(fileSum.truncates) > 0 {
		summary.TruncateTables = append(summary.TruncateTables, TableFileGroup{
			FileName: fileName,
			Tables:   fileSum.truncates,
		})
	}
}

func buildFileOrder(byFile map[string][]ParseIncludeTableBase, fileOrder []string) []string {
	order := lo.Uniq(fileOrder)
	seen := lo.SliceToMap(order, func(s string) (string, struct{}) {
		return s, struct{}{}
	})
	for name := range byFile {
		if _, ok := seen[name]; !ok {
			order = append(order, name)
		}
	}
	return order
}

func summarizeFileStatements(queries []ParseIncludeTableBase, counts map[string]int, includeSQLText bool) (
	fileStatementSummary, error) {
	out := fileStatementSummary{
		alters:    make([]AlterTableRef, 0),
		drops:     make([]TableRef, 0),
		truncates: make([]TableRef, 0),
	}
	currentDb := ""
	for _, q := range queries {
		if q.ErrorCode != 0 {
			return fileStatementSummary{}, fmt.Errorf("%s", q.ErrorMsg)
		}
		if lo.IsEmpty(q.Command) {
			continue
		}
		counts[q.Command]++
		switch q.Command {
		case SQLTypeUseDb:
			if lo.IsNotEmpty(q.DbName) {
				currentDb = q.DbName
			}
		case SQLTypeAlterTable:
			ref := AlterTableRef{
				DbName:    resolveDbName(q.DbName, currentDb),
				TableName: q.TableName,
			}
			if includeSQLText {
				ref.SqlText = q.QueryString
			}
			out.alters = append(out.alters, ref)
		case SQLTypeDropTable:
			out.drops = append(out.drops, tableRefsFromQuery(q, currentDb)...)
		case SQLTypeTruncate:
			out.truncates = append(out.truncates, tableRefsFromQuery(q, currentDb)...)
		}
	}
	return out, nil
}

func resolveDbName(dbName, currentDb string) string {
	if lo.IsNotEmpty(dbName) {
		return dbName
	}
	return currentDb
}

func tableRefsFromQuery(q ParseIncludeTableBase, currentDb string) []TableRef {
	refs := parseQualifiedTables(q.QueryDigestText, currentDb)
	if len(refs) > 0 {
		return refs
	}
	if lo.IsEmpty(q.TableName) {
		return nil
	}
	return []TableRef{{
		DbName:    resolveDbName(q.DbName, currentDb),
		TableName: q.TableName,
	}}
}

// parseQualifiedTables 从 tmysqlparse query_digest_text 提取库表。
// 例：DROP TABLE `db2` . `t2` , `t3` ；TRUNCATE TABLE `t4`
func parseQualifiedTables(digest, currentDb string) []TableRef {
	if lo.IsEmpty(digest) {
		return nil
	}
	matches := qualifiedTableRe.FindAllStringSubmatch(digest, -1)
	if len(matches) == 0 {
		return nil
	}
	refs := make([]TableRef, 0, len(matches))
	for _, m := range matches {
		if m[1] != "" && m[2] != "" {
			refs = append(refs, TableRef{DbName: m[1], TableName: m[2]})
			continue
		}
		refs = append(refs, TableRef{DbName: currentDb, TableName: m[3]})
	}
	return refs
}
