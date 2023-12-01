// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysqlconnlog

import (
	"context"
	"database/sql"
	"log/slog"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/jmoiron/sqlx"
)

var nameMySQLConnLogSize = "mysql-connlog-size"
var nameMySQLConnLogRotate = "mysql-connlog-rotate"

//var nameMySQLConnLogReport = "mysql-connlog-report"

var sizeLimit int64 = 1024 * 1024 * 1024 * 2
var speedLimit int64 = 1024 * 1024 * 10

// Checker TODO
type Checker struct {
	db   *sqlx.DB
	name string
	f    func(*sqlx.DB) (string, error)
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {
	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	var initConnLog sql.NullString
	err = c.db.QueryRowxContext(ctx, `SELECT @@init_connect`).Scan(&initConnLog)
	if err != nil {
		slog.Error("select @@init_connect", slog.String("error", err.Error()))
		return "", err
	}
	slog.Info(
		"select @@init_connect",
		slog.String("init_connect", initConnLog.String),
		slog.Bool("initConnLog valid", initConnLog.Valid),
	)

	if !initConnLog.Valid || initConnLog.String == "" {
		slog.Info("init_connect disabled")
		return "", nil
	}

	return c.f(c.db)
}

// Name TODO
func (c *Checker) Name() string {
	return c.name
}

// NewMySQLConnLogSize TODO
func NewMySQLConnLogSize(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameMySQLConnLogSize,
		f:    mysqlConnLogSize,
	}
}

// NewMySQLConnLogRotate TODO
func NewMySQLConnLogRotate(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameMySQLConnLogRotate,
		f:    mysqlConnLogRotate,
	}
}

//// NewMySQLConnLogReport TODO
//func NewMySQLConnLogReport(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
//	return &Checker{
//		db:   cc.MySqlDB,
//		name: nameMySQLConnLogReport,
//		f:    mysqlConnLogReport,
//	}
//}

// RegisterMySQLConnLogSize TODO
func RegisterMySQLConnLogSize() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return nameMySQLConnLogSize, NewMySQLConnLogSize
}

// RegisterMySQLConnLogRotate TODO
func RegisterMySQLConnLogRotate() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return nameMySQLConnLogRotate, NewMySQLConnLogRotate
}

//// RegisterMySQLConnLogReport TODO
//func RegisterMySQLConnLogReport() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
//	return nameMySQLConnLogReport, NewMySQLConnLogReport
//}
