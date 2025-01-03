// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

// Package rotateslowlog 慢查询切换
package rotateslowlog

import (
	"bytes"
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/jmoiron/sqlx"
)

var name = "rotate-slowlog"

// Dummy TODO
type Dummy struct {
	db *sqlx.DB
}

/*
perl 版本中执行了一系列的操作
my @sqls = (
qq{select \@\@global.slow_query_log into \@sq_log_save},
qq{set global slow_query_log=off},
qq{select sleep(2)},
qq{FLUSH SLOW LOGS},
qq{select sleep(3)},
qq{set global slow_query_log=\@sq_log_save},
);
但是似乎只需要 FLUSH SLOW LOGS
*/

// Run 运行
func (d *Dummy) Run() (msg string, err error) {
	var slowLogPath string
	var slowLogOn bool
	err = d.db.QueryRowx(
		`SELECT @@slow_query_log, @@slow_query_log_file`,
	).Scan(&slowLogOn, &slowLogPath)
	if err != nil {
		slog.Error("query slow_query_log, slow_query_log_file", slog.String("error", err.Error()))
		return "", err
	}
	slog.Info(
		"rotate slow log",
		slog.Bool("slow_query_log", slowLogOn),
		slog.String("slow_query_log_file", slowLogPath),
	)

	if !slowLogOn {
		return "", nil
	}

	slowLogDir := filepath.Dir(slowLogPath)
	slowLogFile := filepath.Base(slowLogPath)

	historySlowLogFilePath := filepath.Join(
		slowLogDir,
		fmt.Sprintf("%s.%d", slowLogFile, time.Now().Weekday()),
	)

	/*
		1. 文件不存在, st == nil, err != nil && os.IsNotExist(err) == true
		2. 文件存在, st != nil, err == nil
	*/
	st, err := os.Stat(historySlowLogFilePath)
	if err != nil {
		if !os.IsNotExist(err) { // 文件存在
			slog.Error("get history slow log file stat",
				slog.String("error", err.Error()),
				slog.String("history file path", historySlowLogFilePath),
			)
			return "", nil
		}
		// 文件不存在
	} else {
		// 3 天只是为了方便, 实际控制的是 1 周 rotate 1 次
		// 短时间连续执行不会重复 rotate
		if time.Now().Sub(st.ModTime()) < 3*24*time.Hour {
			slog.Info(
				"rotate slow log skip too frequency call",
				slog.Time("now", time.Now()),
				slog.Time("history file mod time", st.ModTime()),
				slog.String("history file", historySlowLogFilePath),
			)
			return "", nil
		}
	}

	mvCmd := exec.Command(
		"mv",
		slowLogPath,
		historySlowLogFilePath,
	)

	var stderr bytes.Buffer
	mvCmd.Stderr = &stderr
	err = mvCmd.Run()
	if err != nil {
		slog.Error("mv slow log",
			slog.String("error", err.Error()),
			slog.String("stderr", stderr.String()),
		)
		return "", err
	}

	touchCmd := exec.Command("touch", slowLogPath)
	stderr.Reset()
	touchCmd.Stderr = &stderr
	err = touchCmd.Run()
	if err != nil {
		slog.Error("touch slow log",
			slog.String("error", err.Error()),
			slog.String("stderr", stderr.String()),
		)
		return "", err
	}

	_, err = d.db.Exec(`FLUSH SLOW LOGS`)
	if err != nil {
		slog.Error("flush slow logs", slog.String("error", err.Error()))
		return "", err
	}

	return "", nil
}

// Name 监控项名
func (d *Dummy) Name() string {
	return name
}

// NewRotateSlowLog 新建监控项实例
func NewRotateSlowLog(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Dummy{db: cc.MySqlDB}
}

// RegisterRotateSlowLog 注册监控项
func RegisterRotateSlowLog() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, NewRotateSlowLog
}
