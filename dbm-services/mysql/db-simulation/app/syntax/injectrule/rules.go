/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package injectrule 提供 SQL 注入静态启发式判定（无外部依赖，便于单测）。
package injectrule

import (
	"fmt"
	"regexp"
	"strings"
)

const sqlTypeSelect = "select"

var (
	reSleepOrBenchmark  = regexp.MustCompile(`(?i)\b(SLEEP|BENCHMARK)\s*\(`)
	reIntoOutfile       = regexp.MustCompile(`(?i)\bINTO\s+(OUTFILE|DUMPFILE)\b`)
	reLoadFile          = regexp.MustCompile(`(?i)\bLOAD_FILE\s*\(`)
	reUnion             = regexp.MustCompile(`(?i)\bUNION(\s+ALL)?\b`)
	reInlineHashComment = regexp.MustCompile(`\S.*\s+#`)
	reInlineDashComment = regexp.MustCompile(`\S.*--\s`)
	reTautologyNumParts = regexp.MustCompile(`(?i)\bOR\s+['"]?(\d+)['"]?\s*=\s*['"]?(\d+)['"]?`)
	reTautologyStrParts = regexp.MustCompile(`(?i)\bOR\s+'([^']*)'\s*=\s*'([^']*)'`)
)

// TableReference 表引用
type TableReference struct {
	DbName    string `json:"db_name"`
	TableName string `json:"table_name"`
}

// ParseLine 注入检测用解析行
type ParseLine struct {
	Command         string           `json:"command"`
	QueryString     string           `json:"query_string,omitempty"`
	HasSubQuery     bool             `json:"has_subquery,omitempty"`
	TableReferences []TableReference `json:"table_references,omitempty"`
}

// Result 注入检测结果
type Result struct {
	IsInject bool   `json:"is_inject"`
	Reason   string `json:"reason"`
}

// Evaluate 对解析结果做静态注入启发式判定。
func Evaluate(lines []ParseLine, judgeSubqueryDiffTable bool) Result {
	var reasons []string

	if len(lines) > 1 {
		reasons = append(reasons, fmt.Sprintf("检测到多语句执行（共 %d 条）", len(lines)))
	}

	hasSubqueryNonSelect := false
	for _, line := range lines {
		qs := line.QueryString

		if reUnion.MatchString(qs) {
			reasons = append(reasons, "检测到 UNION 查询拼接")
		}
		if reSleepOrBenchmark.MatchString(qs) {
			reasons = append(reasons, "检测到 SLEEP/BENCHMARK 时间盲注函数")
		}
		if reIntoOutfile.MatchString(qs) {
			reasons = append(reasons, "检测到 INTO OUTFILE/DUMPFILE 文件写出")
		}
		if reLoadFile.MatchString(qs) {
			reasons = append(reasons, "检测到 LOAD_FILE 文件读取")
		}
		if hasInlineCommentEscape(qs) {
			reasons = append(reasons, "检测到行内注释逃逸（# 或 --）")
		}
		if hasTautology(qs) {
			reasons = append(reasons, "检测到恒真条件启发式（如 OR 1=1）")
		}

		if judgeSubqueryDiffTable {
			if line.HasSubQuery && strings.EqualFold(line.Command, sqlTypeSelect) {
				refs := UniqueTableRefs(line.TableReferences)
				if len(refs) > 1 {
					reasons = append(reasons, fmt.Sprintf("子查询引用了不同表：%s", strings.Join(refs, ", ")))
				}
			} else if line.HasSubQuery && !strings.EqualFold(line.Command, sqlTypeSelect) {
				hasSubqueryNonSelect = true
			}
		}
	}

	reasons = uniqStable(reasons)

	if judgeSubqueryDiffTable && hasSubqueryNonSelect && len(reasons) == 0 {
		return Result{
			IsInject: false,
			Reason:   "子查询不同表规则仅支持 SELECT，当前语句未按该规则判定为注入",
		}
	}

	if len(reasons) == 0 {
		return Result{IsInject: false, Reason: ""}
	}
	return Result{
		IsInject: true,
		Reason:   strings.Join(reasons, "; "),
	}
}

func hasInlineCommentEscape(qs string) bool {
	if qs == "" {
		return false
	}
	trimmed := strings.TrimSpace(qs)
	if strings.HasPrefix(trimmed, "#") || strings.HasPrefix(trimmed, "--") {
		return false
	}
	return reInlineHashComment.MatchString(qs) || reInlineDashComment.MatchString(qs)
}

func hasTautology(qs string) bool {
	if qs == "" {
		return false
	}
	if parts := reTautologyStrParts.FindStringSubmatch(qs); len(parts) == 3 && parts[1] == parts[2] {
		return true
	}
	parts := reTautologyNumParts.FindStringSubmatch(qs)
	return len(parts) == 3 && parts[1] == parts[2]
}

// UniqueTableRefs 按 (db, table) 去重；空库名只比表名（小写）
func UniqueTableRefs(refs []TableReference) []string {
	seen := make(map[string]struct{})
	var out []string
	for _, r := range refs {
		tbl := strings.ToLower(strings.TrimSpace(r.TableName))
		if tbl == "" {
			continue
		}
		db := strings.ToLower(strings.TrimSpace(r.DbName))
		key := tbl
		if db != "" {
			key = db + "." + tbl
		}
		if _, ok := seen[key]; ok {
			continue
		}
		dup := false
		if db == "" {
			for k := range seen {
				if k == tbl || strings.HasSuffix(k, "."+tbl) {
					dup = true
					break
				}
			}
		} else if _, ok := seen[tbl]; ok {
			dup = true
		}
		if dup {
			continue
		}
		seen[key] = struct{}{}
		out = append(out, key)
	}
	return out
}

func uniqStable(in []string) []string {
	seen := make(map[string]struct{}, len(in))
	var out []string
	for _, s := range in {
		if _, ok := seen[s]; ok {
			continue
		}
		seen[s] = struct{}{}
		out = append(out, s)
	}
	return out
}
