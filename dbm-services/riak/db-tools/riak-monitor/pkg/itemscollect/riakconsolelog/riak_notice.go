// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package riakconsolelog

import (
	"bufio"
	"dbm-services/riak/db-tools/riak-monitor/pkg/utils"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"golang.org/x/exp/slog"

	"github.com/dlclark/regexp2"
)

var executable string
var offsetRegFile string
var rowStartPattern *regexp2.Regexp
var riakNoticePattern *regexp2.Regexp
var riakNoticeIgnorePattern *regexp2.Regexp

func riakNotice() (string, error) {
	return ScanLog()
}

func init() {
	executable, _ = os.Executable()
	offsetRegFile = filepath.Join(filepath.Dir(executable), "console_log_offset.reg")
	now := time.Now()
	rowStartPattern = regexp2.MustCompile(
		fmt.Sprintf(
			`^(?=(?:(%s|%s|%s)))`,
			now.Format("2006-01-02"),
			now.Format("060102"),
			now.Format("20060102"),
		),
		regexp2.None,
	)
	riakNoticePattern = regexp2.MustCompile(
		fmt.Sprintf(
			`(?=(?:(%s)))`,
			strings.Join(
				[]string{"error", "fatal"},
				"|",
			),
		),
		regexp2.IgnoreCase,
	)
	riakNoticeIgnorePattern = regexp2.MustCompile(
		fmt.Sprintf(
			`(?=(?:(%s)))`,
			strings.Join(
				[]string{"Unrecognized message",
					"no function clause matching webmachine_request",
					"too many siblings for object"},
				"|",
			),
		),
		regexp2.IgnoreCase,
	)
}

// ScanLog 扫描日志
func ScanLog() (string, error) {
	consoleLogPath, err := findConsoleLogFile()
	if err != nil {
		return "", err
	}
	file, offset, err := newScanner(consoleLogPath)
	scanner := bufio.NewScanner(file)
	var lines, infos []string
	// 逐行扫描日志文件
	for scanner.Scan() {
		content := scanner.Bytes()
		line := scanner.Text()
		lines = append(lines, line)
		offset += int64(len(content)) + 1
	}
	file.Close()
	for _, line := range lines {
		match, err := rowStartPattern.MatchString(line)
		if err != nil {
			slog.Error(
				"apply row pattern", err, slog.String("pattern", rowStartPattern.String()),
			)
			continue
		}
		// 非完整一行的读取不做判断
		if !match {
			continue
		}
		// 匹配报错信息
		match, err = riakNoticePattern.MatchString(line)
		if err != nil {
			slog.Error(
				"apply pattern", err, slog.String("pattern", riakNoticePattern.String()),
			)
		}
		if match {
			// 应该忽略的报错信息
			matchignore, err := riakNoticeIgnorePattern.MatchString(line)
			if err != nil {
				slog.Error(
					"apply ignore pattern", err, slog.String("ignore pattern", riakNoticeIgnorePattern.String()),
				)
			}
			if !matchignore {
				infos = append(infos, line)
			}
		}
	}
	// 更新offsetRegFile文件中，下次读取开始的位置
	f, err := os.OpenFile(offsetRegFile, os.O_CREATE|os.O_TRUNC|os.O_RDWR, 0755)
	if err != nil {
		slog.Error("open offset reg", err)
		return "", err
	}
	_, err = f.WriteString(strconv.FormatInt(offset, 10))
	if err != nil {
		slog.Error("update offset reg", err)
		return "", err
	}
	if len(infos) > 0 {
		return strings.Join(infos, "\n"), nil
	}
	return "", nil
}

func findConsoleLogFile() (string, error) {
	cmd := `/usr/sbin/riak config effective | grep '^platform_log_dir' | cut -d '=' -f2 | awk '{print $1}'`
	LogPath, err := utils.ExecShellCommand(false, cmd)
	if err != nil {
		slog.Error("get riak log error", err)
		return LogPath, err
	}
	LogPath = strings.ReplaceAll(LogPath, "\n", "")
	return path.Join(LogPath, "console.log"), nil
}

func newScanner(logPath string) (*os.File, int64, error) {
	f, err := os.Open(logPath)
	if err != nil {
		slog.Error("open console log", err)
		return nil, 0, err
	}

	st, err := f.Stat()
	if err != nil {
		slog.Error("stat of console log", err)
		return nil, 0, err
	}
	consoleLogSize := st.Size()

	lastOffset, err := lastRoundOffset()
	if err != nil {
		return nil, 0, err
	}

	// errlog 应该是被 rotate 了
	if consoleLogSize < lastOffset {
		lastOffset = 0
	}

	// 从lastOffset开始读取文件
	offset, err := f.Seek(lastOffset, 0)
	if err != nil {
		slog.Error("seek err log", err)
		return nil, 0, err
	}
	return f, offset, nil
}

func lastRoundOffset() (int64, error) {
	content, err := os.ReadFile(offsetRegFile)
	if err != nil {
		if os.IsNotExist(err) {
			return 0, nil
		}
		slog.Error("read offset reg", err, slog.String("file", offsetRegFile))
		return 0, err
	}

	r, err := strconv.ParseInt(string(content), 10, 64)
	if err != nil {
		slog.Error("parse last offset", err)
		return 0, err
	}
	return r, nil
}
