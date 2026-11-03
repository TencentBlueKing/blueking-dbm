/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package backupexe

import (
	"bytes"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/klauspost/compress/zstd"
	"github.com/pkg/errors"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// infodbaRewriteMaxFileSize infodba_schema 单个 .zst 备份文件超过该大小，不做改写
const infodbaRewriteMaxFileSize = 2 * 1024 * 1024

// infodbaRewriteMaxDecodedSize 解压后内容超过该大小，不做改写，防止内存占用过大
const infodbaRewriteMaxDecodedSize = 32 * 1024 * 1024

var (
	// infodba_schema.<table>-schema.sql.zst
	reInfodbaTableSchemaFile = regexp.MustCompile(
		`^` + regexp.QuoteMeta(cst.INFODBA_SCHEMA) + `\.[^.]+-schema\.sql` + regexp.QuoteMeta(cst.ZstdSuffix) + `$`)
	// infodba_schema.<table>.00000.sql.zst
	reInfodbaTableDataFile = regexp.MustCompile(
		`^` + regexp.QuoteMeta(cst.INFODBA_SCHEMA) + `\.[^.]+\.\d+\.sql` + regexp.QuoteMeta(cst.ZstdSuffix) + `$`)

	reCreateTable = regexp.MustCompile(`(?m)^CREATE TABLE (?:IF NOT EXISTS )?`)
	reInsertInto  = regexp.MustCompile(`(?m)^INSERT INTO `)
)

// RewriteInfodbaSchema 改写备份中 infodba_schema 的表结构和数据文件
// 建库语句 mydumper 已经是 CREATE DATABASE /*!32312 IF NOT EXISTS*/，无需改写
// 表结构: CREATE TABLE -> CREATE TABLE IF NOT EXISTS
// 数据: INSERT INTO -> REPLACE INTO
// 只处理 .zst 文件，单个文件超过 infodbaRewriteMaxFileSize 忽略
func (l *LogicalDumper) RewriteInfodbaSchema() error {
	if l.cnf.LogicalLoad.SkipRewriteInfodbaSchema {
		logger.Log.Info("SkipRewriteInfodbaSchema is true, skip rewriting infodba_schema")
		return nil
	}
	backupDir := filepath.Join(l.cnf.Public.BackupDir, l.cnf.Public.TargetName())
	files, err := filepath.Glob(filepath.Join(backupDir, cst.INFODBA_SCHEMA+".*"+cst.ZstdSuffix))
	if err != nil {
		return errors.WithMessage(err, "glob infodba_schema files")
	}
	var errList []string
	for _, f := range files {
		baseName := filepath.Base(f)
		var re *regexp.Regexp
		var repl []byte
		if reInfodbaTableSchemaFile.MatchString(baseName) {
			re, repl = reCreateTable, []byte("CREATE TABLE IF NOT EXISTS ")
		} else if reInfodbaTableDataFile.MatchString(baseName) {
			re, repl = reInsertInto, []byte("REPLACE INTO ")
		} else {
			continue
		}
		fi, err := os.Stat(f)
		if err != nil {
			errList = append(errList, err.Error())
			continue
		}
		if !fi.Mode().IsRegular() {
			continue
		}
		if fi.Size() > infodbaRewriteMaxFileSize {
			logger.Log.Warnf("skip rewrite %s, file size %d > %d", f, fi.Size(), infodbaRewriteMaxFileSize)
			continue
		}
		changed, err := rewriteZstdSqlFile(f, re, repl)
		if err != nil {
			logger.Log.Warnf("rewrite %s failed: %s", f, err.Error())
			errList = append(errList, err.Error())
			continue
		}
		if changed {
			logger.Log.Infof("rewrite %s success", f)
		}
	}
	if len(errList) > 0 {
		return errors.New(strings.Join(errList, "; "))
	}
	return nil
}

// rewriteZstdSqlFile 解压 zstFile，按 re 替换为 repl，重新压缩后原子替换原文件
// 内容无变化、或解压后超过 infodbaRewriteMaxDecodedSize 时不改写，返回 false
func rewriteZstdSqlFile(zstFile string, re *regexp.Regexp, repl []byte) (bool, error) {
	compressed, err := os.ReadFile(zstFile)
	if err != nil {
		return false, errors.WithMessagef(err, "read %s", zstFile)
	}
	content, err := zstdDecodeAll(compressed)
	if err != nil {
		if errors.Is(err, zstd.ErrDecoderSizeExceeded) {
			logger.Log.Warnf("skip rewrite %s, decompressed size > %d", zstFile, infodbaRewriteMaxDecodedSize)
			return false, nil
		}
		return false, errors.WithMessagef(err, "decompress %s", zstFile)
	}
	newContent := re.ReplaceAllLiteral(content, repl)
	if bytes.Equal(content, newContent) {
		return false, nil
	}

	newCompressed, err := zstdEncodeAll(newContent)
	if err != nil {
		return false, errors.WithMessagef(err, "compress %s", zstFile)
	}
	// 临时文件名不匹配 infodba_schema.* 表文件规则
	tmpFile := strings.TrimSuffix(zstFile, cst.ZstdSuffix) + ".rewrite_tmp" + cst.ZstdSuffix
	defer func() {
		_ = os.Remove(tmpFile)
	}()
	if err = os.WriteFile(tmpFile, newCompressed, 0644); err != nil {
		return false, errors.WithMessagef(err, "write %s", tmpFile)
	}
	// 从磁盘读回校验重新压缩的文件
	verifyCompressed, err := os.ReadFile(tmpFile)
	if err != nil {
		return false, errors.WithMessagef(err, "verify read %s", tmpFile)
	}
	verifyContent, err := zstdDecodeAll(verifyCompressed)
	if err != nil {
		return false, errors.WithMessagef(err, "verify decompress %s", tmpFile)
	}
	if !bytes.Equal(verifyContent, newContent) {
		return false, errors.Errorf("verify %s: content mismatch", tmpFile)
	}
	if err = os.Rename(tmpFile, zstFile); err != nil {
		return false, errors.WithMessagef(err, "rename %s to %s", tmpFile, zstFile)
	}
	return true, nil
}

// zstdDecodeAll 内存中解压，解压后大小超过 infodbaRewriteMaxDecodedSize 返回 zstd.ErrDecoderSizeExceeded
func zstdDecodeAll(src []byte) ([]byte, error) {
	dec, err := zstd.NewReader(nil,
		zstd.WithDecoderConcurrency(1),
		zstd.WithDecoderMaxMemory(infodbaRewriteMaxDecodedSize))
	if err != nil {
		return nil, err
	}
	defer dec.Close()
	return dec.DecodeAll(src, nil)
}

// zstdEncodeAll 内存中压缩，压缩级别与 gozstd 默认一致
func zstdEncodeAll(src []byte) ([]byte, error) {
	enc, err := zstd.NewWriter(nil,
		zstd.WithEncoderConcurrency(1),
		zstd.WithEncoderLevel(zstd.EncoderLevelFromZstd(3)))
	if err != nil {
		return nil, err
	}
	defer func() {
		_ = enc.Close()
	}()
	return enc.EncodeAll(src, nil), nil
}
