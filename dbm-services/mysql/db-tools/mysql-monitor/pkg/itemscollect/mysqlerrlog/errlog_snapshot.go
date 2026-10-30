// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysqlerrlog

import (
	"bufio"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"

	"github.com/dlclark/regexp2"
)

// offsetRegFilePath 每个监控项独立记录 errlog 扫描位置.
// 不同调度组的 mysql-monitor 进程互不共享 offset 文件,
// 避免互相推进扫描位置导致对方漏扫
func offsetRegFilePath(name string) string {
	return filepath.Join(
		filepath.Dir(executable),
		fmt.Sprintf("errlog_offset.%d.%s.reg", config.MonitorConfig.Port, name),
	)
}

// snapShot 从该监控项上次的扫描位置开始增量扫描 errlog,
// 返回通过行首日期和错误 token 预过滤的行
func snapShot(db *pkg.MySQLMonitorDBH, name string) ([]string, error) {
	errLogPath, err := findErrLogFile(db)
	if err != nil {
		return nil, err
	}
	slog.Info("snap shot err log", slog.String("path", errLogPath), slog.String("item", name))

	offsetFile := offsetRegFilePath(name)
	f, offset, err := newScanner(errLogPath, offsetFile)
	if err != nil {
		return nil, err
	}
	defer func() {
		_ = f.Close()
	}()

	// 每次快照现编译, 进程跨天后日期 pattern 不会失效
	rowStartPattern := regexp2.MustCompile(
		fmt.Sprintf(
			`^(?=(?:(%s|%s|%s)))`,
			time.Now().Format("060102"),
			time.Now().Format("20060102"),
			time.Now().Format("2006-01-02"),
		),
		regexp2.None,
	)

	var lines []string
	reader := bufio.NewReader(f)
	for {
		chunk, rerr := reader.ReadBytes('\n')
		if rerr == io.EOF {
			// MySQL 还在写的半截行: 不处理、offset 不推进, 下一轮重新扫
			break
		}
		if rerr != nil {
			slog.Error("read err log", slog.String("error", rerr.Error()), slog.String("item", name))
			return nil, rerr
		}
		// chunk 自带 \n, 长度即精确偏移, 不能无脑 +1
		offset += int64(len(chunk))
		line := strings.TrimRight(string(chunk), "\r\n")

		startMatch, err := rowStartPattern.MatchString(line)
		if err != nil {
			slog.Error("apply row start pattern", slog.String("error", err.Error()))
			return nil, err
		}

		baseErrTokenMatch, err := baseErrTokenPattern.MatchString(line)
		if err != nil {
			slog.Error("apply base error token pattern", slog.String("error", err.Error()))
			return nil, err
		}

		if startMatch && baseErrTokenMatch {
			lines = append(lines, line)
		}
	}

	err = os.WriteFile(offsetFile, []byte(strconv.FormatInt(offset, 10)), 0755)
	if err != nil {
		slog.Error("update offset reg", slog.String("error", err.Error()))
		return nil, err
	}

	return lines, nil
}

func findErrLogFile(db *pkg.MySQLMonitorDBH) (string, error) {
	var errLogPath, dataDir string
	err := db.QueryRowx(`SELECT @@LOG_ERROR, @@DATADIR`).Scan(&errLogPath, &dataDir)
	if err != nil {
		slog.Error("query log_error, datadir", slog.String("error", err.Error()))
		return "", err
	}

	if !filepath.IsAbs(errLogPath) {
		errLogPath = filepath.Join(dataDir, errLogPath)
	}
	return errLogPath, nil
}

func newScanner(logPath string, offsetFile string) (*os.File, int64, error) {
	f, err := os.Open(logPath)
	if err != nil {
		slog.Error("open err log", slog.String("error", err.Error()))
		return nil, 0, err
	}
	defer func() {
		if err != nil && f != nil {
			_ = f.Close()
		}
	}()

	st, err := f.Stat()
	if err != nil {
		slog.Error("stat of err log", slog.String("error", err.Error()))
		return nil, 0, err
	}
	errLogSize := st.Size()
	slog.Debug("snap shot err log", slog.Int64("err log size", errLogSize))

	lastOffset, err := lastRoundOffset(offsetFile)
	if err != nil {
		return nil, 0, err
	}
	if lastOffset < 0 {
		// offset 文件不存在或内容损坏: 首轮定位到文件尾, 不扫历史, 避免补报历史告警
		lastOffset = errLogSize
	}

	slog.Debug("snap shot err log", slog.Int64("last offset", lastOffset))

	// errlog 应该是被 rotate 了
	if errLogSize < lastOffset {
		lastOffset = 0
	}

	if errLogSize-lastOffset > maxScanSize {
		lastOffset = errLogSize - maxScanSize - 1
	}

	offset, err := f.Seek(lastOffset, 0)
	if err != nil {
		slog.Error("seek err log", slog.String("error", err.Error()))
		return nil, 0, err
	}

	return f, offset, nil
}

func lastRoundOffset(offsetFile string) (int64, error) {
	content, err := os.ReadFile(offsetFile)

	if err != nil {
		if os.IsNotExist(err) {
			return -1, nil
		}
		slog.Error("read offset reg", slog.String("error", err.Error()), slog.String("file", offsetFile))
		return 0, err
	}

	slog.Info("read offset reg", slog.String("offset", string(content)))

	r, err := strconv.ParseInt(string(content), 10, 64)
	if err != nil {
		slog.Warn("parse last offset", slog.String("error", err.Error()))
		return -1, nil
	}

	return r, nil
}
