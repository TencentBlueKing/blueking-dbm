// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysqlerrlog

import (
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/dlclark/regexp2"
	"github.com/jmoiron/sqlx"
)

var executable string
var maxScanSize int64 = 50 * 1024 * 1024
var offsetRegFile string
var errLogRegFile string

//var scanned bool

var rowStartPattern *regexp2.Regexp
var baseErrTokenPattern *regexp2.Regexp

var nameMySQLErrNotice = "mysql-err-notice"
var nameMySQLErrCritical = "mysql-err-critical"
var nameSpiderErrNotice = "spider-err-notice"
var nameSpiderErrWarn = "spider-err-warn"
var nameSpiderErrCritical = "spider-err-critical"

var nameMySQLDRestart = "mysqld-restarted"

var mysqlNoticePattern *regexp2.Regexp
var mysqlCriticalExcludePattern *regexp2.Regexp
var spiderNoticePattern *regexp2.Regexp
var spiderWarnPattern *regexp2.Regexp
var spiderCriticalPattern *regexp2.Regexp
var mysqldRestartPattern *regexp2.Regexp

var once sync.Once
var snapShotErr error

func init() {
	executable, _ = os.Executable()

	now := time.Now()
	rowStartPattern = regexp2.MustCompile(
		fmt.Sprintf(
			`^(?=(?:(%s|%s|%s)))`,
			now.Format("060102"),
			now.Format("20060102"),
			now.Format("2006-01-02"),
		),
		regexp2.None,
	)

	baseErrTokenPattern = regexp2.MustCompile(
		fmt.Sprintf(
			`(?=(?:(%s)))`,
			strings.Join(
				[]string{"error", "warn", "fail", "restarted", "hanging", "locked"},
				"|",
			),
		),
		regexp2.IgnoreCase,
	)

	spiderNoticePattern = regexp2.MustCompile(
		fmt.Sprintf(
			`(?=(?:(%s)))`,
			strings.Join(
				[]string{"Got error 12701", "Got error 1159"},
				"|",
			),
		),
		regexp2.IgnoreCase,
	)

	spiderWarnPattern = regexp2.MustCompile(
		fmt.Sprintf(
			`(?=(?:(%s)))`,
			strings.Join(
				[]string{"ERROR SPIDER RESULT", "Got error 1317", "Got error 1146"},
				"|",
			),
		),
		regexp2.IgnoreCase,
	)

	spiderCriticalPattern = regexp2.MustCompile(
		fmt.Sprintf(
			`(?=(?:(%s)))`,
			strings.Join(
				[]string{"2014 Commands out of sync", "Table has no partition"},
				"|",
			),
		),
		regexp2.IgnoreCase,
	)

	//scanned = false
}

// Checker TODO
type Checker struct {
	db   *sqlx.DB
	name string
	f    func() (string, error)
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {
	offsetRegFile = filepath.Join(
		filepath.Dir(executable),
		fmt.Sprintf("errlog_offset.%d.reg", config.MonitorConfig.Port),
	)
	errLogRegFile = filepath.Join(filepath.Dir(executable),
		fmt.Sprintf("errlog.%d.reg", config.MonitorConfig.Port),
	)

	once.Do(func() {
		snapShotErr = snapShot(c.db)
	})
	//err = snapShot(c.db)
	if snapShotErr != nil {
		slog.Error(c.name, slog.String("error", snapShotErr.Error()))
		return "", snapShotErr
	}

	return c.f()
}

// Name TODO
func (c *Checker) Name() string {
	return c.name
}

// NewMySQLErrNotice TODO
func NewMySQLErrNotice(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameMySQLErrNotice,
		f:    mysqlNotice,
	}
}

// NewMySQLErrCritical TODO
func NewMySQLErrCritical(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameMySQLErrCritical,
		f:    mysqlCritical,
	}
}

// NewSpiderErrNotice TODO
func NewSpiderErrNotice(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameSpiderErrNotice,
		f:    spiderNotice,
	}
}

// NewSpiderErrWarn TODO
func NewSpiderErrWarn(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameSpiderErrWarn,
		f:    spiderWarn,
	}
}

// NewSpiderErrCritical TODO
func NewSpiderErrCritical(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameSpiderErrCritical,
		f:    spiderCritical,
	}
}

func NewMySQLDRestartWarn(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameMySQLDRestart,
		f:    mysqldRestart,
	}
}

// RegisterMySQLErrNotice TODO
func RegisterMySQLErrNotice() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return nameMySQLErrNotice, NewMySQLErrNotice
}

// RegisterMySQLErrCritical TODO
func RegisterMySQLErrCritical() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return nameMySQLErrCritical, NewMySQLErrCritical
}

// RegisterSpiderErrNotice TODO
func RegisterSpiderErrNotice() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return nameSpiderErrNotice, NewSpiderErrNotice
}

// RegisterSpiderErrWarn TODO
func RegisterSpiderErrWarn() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return nameSpiderErrWarn, NewSpiderErrWarn
}

// RegisterSpiderErrCritical TODO
func RegisterSpiderErrCritical() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return nameSpiderErrCritical, NewSpiderErrCritical
}

func RegisterMySQLDRestartWarn() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return nameMySQLDRestart, NewMySQLDRestartWarn
}
