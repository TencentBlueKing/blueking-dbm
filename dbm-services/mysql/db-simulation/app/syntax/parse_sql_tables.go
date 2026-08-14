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

	"dbm-services/common/go-pubpkg/logger"
)

// DoParseSQLTables 对本地 SQL 文件执行 tmysqlparse，原样返回每行 ParseIncludeTableBase。
// 不做库表聚合，不收集外键引用表。
func (tf *TmysqlParseFile) DoParseSQLTables(version string) (queries []ParseIncludeTableBase, err error) {
	byFile, err := tf.DoParseSQLTablesByFile(version)
	if err != nil {
		return nil, err
	}
	for _, fileName := range tf.uniqueFileNames() {
		queries = append(queries, byFile[fileName]...)
	}
	return queries, nil
}

// DoParseSQLTablesByFile 对 SQL 文件执行 tmysqlparse，按文件名保留解析行，不打平。
func (tf *TmysqlParseFile) DoParseSQLTablesByFile(version string) (
	byFile map[string][]ParseIncludeTableBase, err error) {
	tf.result = make(map[string]*CheckInfo)
	tf.tmpWorkdir = tf.BaseWorkdir
	tf.mu = sync.Mutex{}

	if !tf.IsLocalFile {
		if err = tf.Init(); err != nil {
			logger.Error("Do init failed %s", err.Error())
			return nil, err
		}
		if err = tf.Downloadfile(); err != nil {
			logger.Error("failed to download sql file from the product library %s", err.Error())
			return nil, err
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

	byFile = make(map[string][]ParseIncludeTableBase)
	for fileName := range executedSqlFileChan {
		items, perr := tf.parseIncludeTableLines(fileName, version)
		if perr != nil {
			return nil, perr
		}
		byFile[fileName] = items
	}
	if execErr != nil {
		return nil, execErr
	}
	return byFile, nil
}

// parseIncludeTableLines 逐行读取 tmysqlparse NDJSON 输出，反序列化为 ParseIncludeTableBase。
func (t *TmysqlParse) parseIncludeTableLines(inputFileName, mysqlVersion string) (
	queries []ParseIncludeTableBase, err error) {
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
					item, uerr := unmarshalIncludeTableLine(line)
					if uerr != nil {
						return nil, uerr
					}
					queries = append(queries, item)
				}
				break
			}
			logger.Error("read Line Error %s", errx.Error())
			return nil, errx
		}
		if len(line) == 1 && line[0] == byte('\n') {
			continue
		}
		item, uerr := unmarshalIncludeTableLine(line)
		if uerr != nil {
			return nil, uerr
		}
		queries = append(queries, item)
	}
	return queries, nil
}

func unmarshalIncludeTableLine(line []byte) (ParseIncludeTableBase, error) {
	var baseRes ParseIncludeTableBase
	if err := json.Unmarshal(line, &baseRes); err != nil {
		logger.Error("json unmarshal line:%s failed %s", string(line), err.Error())
		return baseRes, err
	}
	return baseRes, nil
}
