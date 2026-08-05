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
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"github.com/samber/lo"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app/syntax/injectrule"
)

// DoInjectCheck 对本地 SQL 文件执行 tmysqlparse，并做静态注入启发式检测。
func (tf *TmysqlParseFile) DoInjectCheck(version string, judgeSubqueryDiffTable bool) (InjectCheckResult, error) {
	tf.result = make(map[string]*CheckInfo)
	tf.tmpWorkdir = tf.BaseWorkdir
	tf.mu = sync.Mutex{}

	if !tf.IsLocalFile {
		if err := tf.Init(); err != nil {
			logger.Error("Do init failed %s", err.Error())
			return InjectCheckResult{}, err
		}
		if err := tf.Downloadfile(); err != nil {
			logger.Error("failed to download sql file from the product library %s", err.Error())
			return InjectCheckResult{}, err
		}
	}

	executedSqlFileChan := make(chan string, len(tf.uniqueFileNames()))
	var execErr error
	go func() {
		execErr = tf.Execute(executedSqlFileChan, version)
		if execErr != nil {
			logger.Error("failed to execute tmysqlparse: %s", execErr.Error())
		}
		close(executedSqlFileChan)
	}()

	var lines []InjectParseLine
	for fileName := range executedSqlFileChan {
		items, perr := tf.parseInjectLines(fileName, version)
		if perr != nil {
			return InjectCheckResult{}, perr
		}
		lines = append(lines, items...)
	}
	if execErr != nil {
		return InjectCheckResult{}, execErr
	}
	for _, line := range lines {
		if line.ErrorCode != 0 {
			msg := line.ErrorMsg
			if msg == "" {
				msg = fmt.Sprintf("sql syntax error, error_code=%d", line.ErrorCode)
			}
			return InjectCheckResult{}, fmt.Errorf("%s", msg)
		}
	}
	return EvaluateInjectRules(lines, judgeSubqueryDiffTable), nil
}

// parseInjectLines 逐行读取 tmysqlparse NDJSON，反序列化为 InjectParseLine。
func (t *TmysqlParse) parseInjectLines(inputFileName, mysqlVersion string) (queries []InjectParseLine, err error) {
	filePath := t.getAbsOutputFilePath(inputFileName, mysqlVersion)
	cleanPath := filepath.Clean(filePath)
	baseDir := filepath.Clean(t.tmpWorkdir)
	if t.tmpWorkdir == "" {
		baseDir = filepath.Clean(t.BaseWorkdir)
	}
	if !strings.HasPrefix(cleanPath, baseDir+string(filepath.Separator)) && cleanPath != baseDir {
		logger.Error("attempted path traversal attack: %s", cleanPath)
		return nil, fmt.Errorf("invalid file path")
	}
	fi, errx := os.Stat(cleanPath)
	if errx != nil {
		logger.Error("file stat failed: %s", errx.Error())
		return nil, errx
	}
	if fi.IsDir() {
		logger.Error("path is directory: %s", cleanPath)
		return nil, fmt.Errorf("invalid file type")
	}

	f, err := os.OpenFile(cleanPath, os.O_RDONLY, 0400)
	if err != nil {
		logger.Error("open file failed: %s", err.Error())
		return nil, err
	}
	defer f.Close()

	reader := bufio.NewReader(f)
	for {
		line, errx := reader.ReadBytes(byte('\n'))
		if errx != nil {
			if errx == io.EOF {
				if len(line) > 0 {
					item, uerr := unmarshalInjectLine(line)
					if uerr != nil {
						return nil, uerr
					}
					if shouldKeepInjectLine(item) {
						queries = append(queries, item)
					}
				}
				break
			}
			logger.Error("read Line Error %s", errx.Error())
			return nil, errx
		}
		if len(line) == 1 && line[0] == byte('\n') {
			continue
		}
		item, uerr := unmarshalInjectLine(line)
		if uerr != nil {
			return nil, uerr
		}
		if shouldKeepInjectLine(item) {
			queries = append(queries, item)
		}
	}
	return queries, nil
}

func unmarshalInjectLine(line []byte) (InjectParseLine, error) {
	var baseRes InjectParseLine
	if err := json.Unmarshal(line, &baseRes); err != nil {
		logger.Error("json unmarshal line:%s failed %s", string(line), err.Error())
		return baseRes, err
	}
	return baseRes, nil
}

// shouldKeepInjectLine 过滤仅含版本元信息、无 command 的尾行
func shouldKeepInjectLine(item InjectParseLine) bool {
	if item.ErrorCode != 0 {
		return true
	}
	return lo.IsNotEmpty(item.Command)
}

// EvaluateInjectRules 对解析结果做静态注入启发式判定。
func EvaluateInjectRules(lines []InjectParseLine, judgeSubqueryDiffTable bool) InjectCheckResult {
	ruleLines := make([]injectrule.ParseLine, 0, len(lines))
	for _, line := range lines {
		refs := make([]injectrule.TableReference, 0, len(line.TableReferences))
		for _, r := range line.TableReferences {
			refs = append(refs, injectrule.TableReference{
				DbName:    r.DbName,
				TableName: r.TableName,
			})
		}
		ruleLines = append(ruleLines, injectrule.ParseLine{
			Command:         line.Command,
			QueryString:     line.QueryString,
			HasSubQuery:     line.HasSubQuery,
			TableReferences: refs,
		})
	}
	got := injectrule.Evaluate(ruleLines, judgeSubqueryDiffTable)
	return InjectCheckResult{
		IsInject: got.IsInject,
		Reason:   got.Reason,
	}
}
