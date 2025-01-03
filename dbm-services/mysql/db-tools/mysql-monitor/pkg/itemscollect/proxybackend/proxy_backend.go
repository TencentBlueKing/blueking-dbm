// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

// Package proxybackend proxy后端
package proxybackend

import (
	"bufio"
	"fmt"
	"log/slog"
	"math/big"
	"net"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/utils"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
)

var name = "proxy-backend"

// Checker TODO
type Checker struct {
	db *sqlx.DB
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {
	cnfPath := filepath.Join("/etc", fmt.Sprintf(`proxy.cnf.%d`, config.MonitorConfig.Port))
	f, err := os.Open(cnfPath)
	if err != nil {
		slog.Error("open proxy cnf file", slog.String("error", err.Error()))
		return "", err
	}
	defer func() {
		_ = f.Close()
	}()

	var backendLine string
	pattern := regexp.MustCompile(`^proxy-backend-addresses.*`)
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := scanner.Text()
		if err := scanner.Err(); err != nil {
			slog.Error("scan proxy cnf file", slog.String("error", err.Error()))
			return "", err
		}

		if pattern.MatchString(line) {
			backendLine = strings.TrimSpace(line)
			break
		}
	}

	if backendLine == "" {
		err := errors.Errorf("proxy-backend-addresses not found in cnf")
		slog.Error("find backend in cnf", slog.String("error", err.Error()))
		return "", nil
	}

	splitPattern := regexp.MustCompile(`\s*=\s*`)
	splitLine := splitPattern.Split(backendLine, -1)
	if len(splitLine) != 2 {
		err := errors.Errorf("invalid config: %s", backendLine)
		slog.Error("split proxy-backend-addresses", slog.String("error", err.Error()))
		return "", nil
	}

	backendAddr := splitLine[1]

	backendInfo := make(map[string]interface{})
	err = c.db.QueryRowx(
		`SELECT * FROM BACKENDS`,
	).MapScan(backendInfo)
	if err != nil {
		slog.Error("query backends", slog.String("error", err.Error()))
		return "", err
	}

	slog.Info("query backends: %v", slog.Any("backend info", backendInfo))

	b, ok := backendInfo["address"].([]byte)
	queryAddr := string(b)
	slog.Info("query backends", slog.String("query addr", queryAddr))
	if backendAddr == "" || !ok || backendAddr != queryAddr {
		slog.Info("query backends",
			slog.String("query addr", queryAddr),
			slog.Bool("ok", ok),
		)
		msg = fmt.Sprintf("cnf.backend=%s, mem.backend=%s", backendAddr, queryAddr)
		return msg, nil
	}

	backendIp := strings.Split(backendAddr, ":")[0]
	if net.ParseIP(backendIp) == nil {
		msg = fmt.Sprintf("%s not a valid ip", backendIp)
		return msg, nil
	}
	if net.ParseIP(backendIp).To4() == nil {
		msg = fmt.Sprintf("%s not a v4 ip", backendIp)
		return msg, nil
	}

	utils.SendMonitorMetrics(
		"proxy_backend_ip",
		big.NewInt(0).SetBytes(net.ParseIP(backendIp).To4()).Int64(),
		nil,
	)

	return msg, nil
}

// Name TODO
func (c *Checker) Name() string {
	return name
}

// New TODO
func New(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{db: cc.ProxyAdminDB}
}

// Register TODO
func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, New
}
