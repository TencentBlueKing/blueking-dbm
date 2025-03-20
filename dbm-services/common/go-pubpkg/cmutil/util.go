/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package cmutil TODO
package cmutil

import (
	"strings"
	"time"

	"github.com/spf13/cast"

	"dbm-services/common/go-pubpkg/logger"

	"github.com/pkg/errors"
)

// RetryConfig TODO
type RetryConfig struct {
	Times     int           // 重试次数
	DelayTime time.Duration // 每次重试间隔
}

// RetriesExceeded TODO
// retries exceeded
const RetriesExceeded = "retries exceeded"

// Retry 重试
// 第 0 次也需要 delay 再运行
func Retry(r RetryConfig, f func() error) (err error) {
	for i := 0; i < r.Times; i++ {
		if err = f(); err == nil {
			return nil
		}
		logger.Warn("第%d次重试,函数错误:%s", i, err.Error())
		time.Sleep(r.DelayTime)
	}
	if err != nil {
		return errors.Wrap(err, RetriesExceeded)
	}
	return
}

// DecreasingRetry 递减Sleep重试
func DecreasingRetry() (err error) {
	return
}

// GrepLines 日志过滤
type GrepLines struct {
	// FilePath	日志文件路径
	FilePath string
	// IgnoreCase 是否忽略大小写, 默认false大小写敏感
	IgnoreCase bool
	// FromHead from head or tail，默认false从 tail 里面取
	FromHead bool
}

// NewGrepLines 日志过滤，从文件里面 grep 错误关键字
func NewGrepLines(filePath string, ignoreCase, fromHead bool) *GrepLines {
	return &GrepLines{
		FilePath:   filePath,
		IgnoreCase: ignoreCase,
		FromHead:   fromHead,
	}
}

// MatchWordsExclude 从文件里面 grep 排除关键字
func (g *GrepLines) MatchWordsExclude(keyWordsExclude []string, linesRet int) (string, error) {
	var grepCommand []string
	lineNum := "-" + cast.ToString(linesRet)
	if len(keyWordsExclude) > 0 {
		grepExpr := "'" + strings.Join(keyWordsExclude, "|") + "'"
		if g.IgnoreCase {
			grepCommand = append(grepCommand, "grep", "-Evi")
		} else {
			grepCommand = append(grepCommand, "grep", "-Ev")
		}
		grepCommand = append(grepCommand, grepExpr, g.FilePath)
		if g.FromHead {
			grepCommand = append(grepCommand, "|", "head", lineNum)
		} else {
			grepCommand = append(grepCommand, "|", "tail", lineNum)
		}
	} else {
		if g.FromHead {
			grepCommand = append(grepCommand, "head", lineNum, g.FilePath)
		} else {
			grepCommand = append(grepCommand, "tail", lineNum, g.FilePath)
		}
	}
	errStrDetail, cmdStdErr, err := ExecCommand(true, "", grepCommand[0], grepCommand[1:]...)
	errStrDetail = strings.TrimSpace(errStrDetail)
	if errStrDetail != "" {
		return errStrDetail, nil
	} else {
		return "", errors.WithMessage(err, cmdStdErr)
	}
}

// MatchWords 从文件里面 grep 错误关键字
// 如果不指定 keywords，则直接 tail / head 文件行
func (g *GrepLines) MatchWords(keywords []string, linesRet int) (string, error) {
	var grepCommand []string
	lineNum := "-" + cast.ToString(linesRet)
	if len(keywords) > 0 {
		grepExpr := "'" + strings.Join(keywords, "|") + "'"
		if g.IgnoreCase {
			grepCommand = append(grepCommand, "grep", "-Ei")
		} else {
			grepCommand = append(grepCommand, "grep", "-E")
		}
		grepCommand = append(grepCommand, grepExpr, g.FilePath)
		if g.FromHead {
			grepCommand = append(grepCommand, "|", "head", lineNum)
		} else {
			grepCommand = append(grepCommand, "|", "tail", lineNum)
		}
	} else {
		if g.FromHead {
			grepCommand = append(grepCommand, "head", lineNum, g.FilePath)
		} else {
			grepCommand = append(grepCommand, "tail", lineNum, g.FilePath)
		}
	}
	errStrDetail, cmdStdErr, err := ExecCommand(true, "", grepCommand[0], grepCommand[1:]...)
	errStrDetail = strings.TrimSpace(errStrDetail)
	if errStrDetail != "" {
		return errStrDetail, nil
	} else {
		return "", errors.WithMessage(err, cmdStdErr)
	}
}
