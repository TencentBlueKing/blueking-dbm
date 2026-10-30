// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysqlerrlog

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"fmt"
	"log/slog"
	"os"
	"strings"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/dlclark/regexp2"
)

var executable string
var maxScanSize int64 = 50 * 1024 * 1024

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

func init() {
	executable, _ = os.Executable()

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
	db      *pkg.MySQLMonitorDBH
	name    string
	pattern *regexp2.Regexp
}

// Run TODO
func (c *Checker) Run() (warnDB *pkg.MySQLMonitorDBH, msg string, err error) {
	lines, err := snapShot(c.db, c.name)
	if err != nil {
		slog.Error(c.name, slog.String("error", err.Error()))
		return nil, "", err
	}

	msg, err = scanSnapShot(c.name, c.pattern, lines)
	return nil, msg, err
}

// Name TODO
func (c *Checker) Name() string {
	return c.name
}

// NewMySQLErrNotice TODO
func NewMySQLErrNotice(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:      cc.MySqlDB,
		name:    nameMySQLErrNotice,
		pattern: mysqlNoticePattern,
	}
}

// NewMySQLErrCritical TODO
func NewMySQLErrCritical(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:      cc.MySqlDB,
		name:    nameMySQLErrCritical,
		pattern: mysqlCriticalExcludePattern,
	}
}

// NewSpiderErrNotice TODO
func NewSpiderErrNotice(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:      cc.MySqlDB,
		name:    nameSpiderErrNotice,
		pattern: spiderNoticePattern,
	}
}

// NewSpiderErrWarn TODO
func NewSpiderErrWarn(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:      cc.MySqlDB,
		name:    nameSpiderErrWarn,
		pattern: spiderWarnPattern,
	}
}

// NewSpiderErrCritical TODO
func NewSpiderErrCritical(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:      cc.MySqlDB,
		name:    nameSpiderErrCritical,
		pattern: spiderCriticalPattern,
	}
}

func NewMySQLDRestartWarn(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:      cc.MySqlDB,
		name:    nameMySQLDRestart,
		pattern: mysqldRestartPattern,
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
