// Package mysql_rpc
/*
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
*/
package mysql_rpc

import (
	"dbm-services/mysql/db-remote-service/pkg/config"
	"dbm-services/mysql/db-remote-service/pkg/rpc_core"
	"fmt"
	"log/slog"
	"net/url"
	"regexp"
	"slices"
	"strings"
	"time"

	_ "github.com/go-sql-driver/mysql" // mysql
	"github.com/jmoiron/sqlx"
)

// MySQLRPCEmbed mysql 实现
type MySQLRPCEmbed struct {
}

// MakeConnection mysql 建立连接
func (c *MySQLRPCEmbed) MakeConnection(address string, user string, password string, timeout int, timezone string) (*sqlx.DB, error) {
	connectParam := fmt.Sprintf(
		"timeout=%ds&time_zone='%s'",
		timeout, url.QueryEscape(timezone),
	)

	retryTimes := 0

CONNSTART:
	if retryTimes > 3 {
		return nil, fmt.Errorf("failed to connect to mysql server after %d retries", retryTimes)
	}
	retryTimes++

	db, err := sqlx.Open(
		"mysql",
		fmt.Sprintf(`%s:%s@tcp(%s)/?%s`, user, password, address, connectParam),
	)
	if err != nil {
		slog.Warn("first time connect to mysql",
			slog.String("err", err.Error()),
			slog.String("address", address),
			slog.String("user", user),
			slog.String("password", password),
		)

		time.Sleep(2 * time.Second)
		goto CONNSTART
	}

	_, err = db.Queryx("SELECT 1")
	if err != nil {
		slog.Warn("try select 1 failed", slog.String("err", err.Error()), slog.String("address", address))
		time.Sleep(2 * time.Second)
		goto CONNSTART
	}

	return db, nil
}

// ParseCommand mysql 解析命令
func (c *MySQLRPCEmbed) ParseCommand(command string) (*rpc_core.ParseQueryBase, error) {
	return &rpc_core.ParseQueryBase{
		QueryId:   0,
		Command:   command,
		ErrorCode: 0,
		ErrorMsg:  "",
	}, nil
}

// IsQueryCommand mysql 解析命令
func (c *MySQLRPCEmbed) IsQueryCommand(pc *rpc_core.ParseQueryBase) bool {
	return isQueryCommand(pc.Command)
}

// IsExecuteCommand mysql 解析命令
func (c *MySQLRPCEmbed) IsExecuteCommand(pc *rpc_core.ParseQueryBase) bool {
	return !isQueryCommand(pc.Command)
}

// User mysql 用户
func (c *MySQLRPCEmbed) User() string {
	return config.RuntimeConfig.MySQLAdminUser
}

// Password mysql 密码
func (c *MySQLRPCEmbed) Password() string {
	return config.RuntimeConfig.MySQLAdminPassword
}

func isQueryCommand(command string) bool {
	pattern := regexp.MustCompile(`\s+`)
	firstWord := strings.ToLower(pattern.Split(command, -1)[0])
	if firstWord == "tdbctl" {
		return isTDBCTLQuery(command)
	} else {
		return slices.Index(genericDoQueryCommand, firstWord) >= 0
	}
}

func isTDBCTLQuery(command string) bool {
	splitPattern := regexp.MustCompile(`\s+`)
	secondWord := strings.ToLower(splitPattern.Split(command, -1)[1])
	switch secondWord {
	case "get", "show":
		return true
	case "connect":
		catchPattern := regexp.MustCompile(`(?mi)^.*execute\s+['"](.*)['"]$`)
		executeCmd := catchPattern.FindAllStringSubmatch(command, -1)[0][1]
		return isQueryCommand(executeCmd)
	default:
		return false
	}
}
