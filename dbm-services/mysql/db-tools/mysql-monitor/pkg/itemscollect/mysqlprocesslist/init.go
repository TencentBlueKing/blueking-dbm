// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysqlprocesslist

import (
	"os"
	"sync"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/jmoiron/sqlx"
)

// var stored = false
var executable string

var nameMySQLLock = "mysql-lock"
var nameMySQLInject = "mysql-inject"

var once sync.Once
var snapShotErr error

func init() {
	executable, _ = os.Executable()
}

// Checker TODO
type Checker struct {
	db   *sqlx.DB
	name string
	f    func() (string, error)
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {
	once.Do(func() {
		snapShotErr = snapShot(c.db)
	})

	if snapShotErr != nil {
		return "", snapShotErr
	}
	return c.f()
}

// Name TODO
func (c *Checker) Name() string {
	return c.name
}

// NewMySQLLock TODO
func NewMySQLLock(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameMySQLLock,
		f:    mysqlLock,
	}
}

// NewMySQLInject TODO
func NewMySQLInject(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameMySQLInject,
		f:    mysqlInject,
	}
}

// RegisterMySQLLock TODO
func RegisterMySQLLock() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return nameMySQLLock, NewMySQLLock
}

// RegisterMySQLInject TODO
func RegisterMySQLInject() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return nameMySQLInject, NewMySQLInject
}
