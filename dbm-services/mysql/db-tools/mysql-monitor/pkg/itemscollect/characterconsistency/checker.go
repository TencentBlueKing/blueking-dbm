// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package characterconsistency

import (
	"fmt"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
)

var name = "character-consistency"

// Checker TODO
type Checker struct {
	db *sqlx.DB
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {

	var characterSetServer string
	err = c.db.Get(&characterSetServer, `SELECT @@character_set_server`)
	if err != nil {
		return "", errors.Wrap(err, "get character_set_server") // ToDo 这里需要发告警么?
	}

	q, args, err := sqlx.In(
		`SELECT SCHEMA_NAME, DEFAULT_CHARACTER_SET_NAME 
					FROM INFORMATION_SCHEMA.SCHEMATA 
					WHERE DEFAULT_CHARACTER_SET_NAME <> ? AND SCHEMA_NAME NOT IN (?)`,
		characterSetServer,
		config.MonitorConfig.DBASysDbs,
	)
	if err != nil {
		return "", errors.Wrap(err, "build IN query db charset")
	}

	var res []struct {
		SchemaName    string `db:"SCHEMA_NAME"`
		SchemaCharset string `db:"DEFAULT_CHARACTER_SET_NAME"`
	}
	err = c.db.Select(&res, c.db.Rebind(q), args...)
	if err != nil {
		return "", errors.Wrap(err, "query charset inconsistent dbs")
	}

	if len(res) > 0 {
		return fmt.Sprintf("%v charset inconsistent with server charset", res), nil
	} else {
		return "", nil
	}
}

// Name TODO
func (c *Checker) Name() string {
	return name
}

// New TODO
func New(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{db: cc.MySqlDB}
}

// Register TODO
func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, New
}
