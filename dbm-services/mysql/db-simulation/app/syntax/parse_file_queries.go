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
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
	"path"
	"strings"
	"sync"

	"dbm-services/mysql/db-simulation/app/syntax/injectrule"
)

const (
	printQueryLengthLimit = 1048576
	queryTruncatedCode    = 1
)

// ParseFileQuery 一条语句的解析结果，附带按单条判定的注入结果。
type ParseFileQuery struct {
	QueryID         int              `json:"query_id"`
	Command         string           `json:"command"`
	DbName          string           `json:"db_name"`
	ErrorCode       int              `json:"error_code"`
	ErrorMsg        string           `json:"error_msg"`
	TableReferences []TableReference `json:"table_references"`
	QueryDigestText string           `json:"query_digest_text"`
	QueryString     string           `json:"query_string"`
	IsInject        bool             `json:"is_inject"`
	Reason          string           `json:"reason"`
}

// DoParseFileQueries 解析 SQL 文件并按语句返回。
// 每条单独做注入判定，避免整文件被当成多语句注入。
func (tf *TmysqlParseFile) DoParseFileQueries(version string) ([]ParseFileQuery, error) {
	tf.PrintQueryLength = printQueryLengthLimit
	tf.result = make(map[string]*CheckInfo)
	tf.tmpWorkdir = tf.BaseWorkdir
	tf.mu = sync.Mutex{}
	if !tf.IsLocalFile {
		if err := tf.Init(); err != nil {
			return nil, err
		}
		if err := tf.Downloadfile(); err != nil {
			return nil, err
		}
	}

	executed := make(chan string, len(tf.uniqueFileNames()))
	if err := tf.Execute(executed, version); err != nil {
		return nil, err
	}
	close(executed)
	for range executed {
	}

	var out []ParseFileQuery
	for _, fileName := range tf.uniqueFileNames() {
		lines, err := tf.parseInjectLines(fileName, version)
		if err != nil {
			return nil, err
		}
		for _, line := range lines {
			out = append(out, buildFileQuery(line))
		}
	}
	if out == nil {
		out = []ParseFileQuery{}
	}
	return out, nil
}

func buildFileQuery(line InjectParseLine) ParseFileQuery {
	refs := line.TableReferences
	if refs == nil {
		refs = []TableReference{}
	}
	item := ParseFileQuery{
		QueryID:         line.QueryId,
		Command:         line.Command,
		DbName:          line.DbName,
		ErrorCode:       line.ErrorCode,
		ErrorMsg:        line.ErrorMsg,
		TableReferences: refs,
		QueryDigestText: line.QueryDigestText,
		QueryString:     line.QueryString,
	}
	if len(line.QueryString) >= printQueryLengthLimit {
		item.QueryString = ""
		item.ErrorCode = queryTruncatedCode
		item.ErrorMsg = "语句超过解析长度上限，已截断"
		return item
	}
	if item.ErrorCode != 0 {
		return item
	}
	item.IsInject, item.Reason = exportInject(line)
	return item
}

// ParseFileQueriesResult 是解析接口返回的文件字节哈希和语句列表。
type ParseFileQueriesResult struct {
	ContentSHA256 string           `json:"content_sha256"`
	Queries       []ParseFileQuery `json:"queries"`
}

// ContentSHA256 对这次实际读到的 SQL 文件字节计算 SHA-256。
func (tf *TmysqlParseFile) ContentSHA256() (string, error) {
	names := tf.uniqueFileNames()
	if len(names) != 1 {
		return "", fmt.Errorf("parse file queries expects one sql file")
	}
	raw, err := os.ReadFile(tf.sqlFilePath(names[0]))
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:]), nil
}

func (tf *TmysqlParseFile) sqlFilePath(fileName string) string {
	base := tf.tmpWorkdir
	if tf.IsLocalFile {
		base = tf.BaseWorkdir
	}
	return path.Join(base, fileName)
}

func exportInject(line InjectParseLine) (bool, string) {
	refs := make([]injectrule.TableReference, 0, len(line.TableReferences))
	for _, ref := range line.TableReferences {
		refs = append(refs, injectrule.TableReference{
			DbName:    ref.DbName,
			TableName: ref.TableName,
		})
	}
	got := injectrule.Evaluate([]injectrule.ParseLine{{
		Command:         line.Command,
		QueryString:     line.QueryString,
		HasSubQuery:     line.HasSubQuery,
		TableReferences: refs,
	}}, false)
	if !got.IsInject {
		return false, ""
	}
	var keep []string
	for _, part := range strings.Split(got.Reason, "; ") {
		if part == "" {
			continue
		}
		if strings.Contains(part, "UNION 查询拼接") ||
			strings.Contains(part, "恒真条件") ||
			strings.Contains(part, "多语句执行") {
			continue
		}
		keep = append(keep, part)
	}
	if len(keep) == 0 {
		return false, ""
	}
	return true, strings.Join(keep, "; ")
}
