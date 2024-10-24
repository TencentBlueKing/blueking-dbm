// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

// Package mysqlconfigdiff 配置检查
package mysqlconfigdiff

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"strings"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/pkg/errors"
)

var name = "mysql-config-diff"
var executable string
var importantVariables []string

func init() {
	executable, _ = os.Executable()
	importantVariables = []string{
		"binlog_format",
		"max_connections",
		"character_set_server",
		"log_bin",
		"sql_log_bin",
		"default_storage_engine",
		"transaction_isolation",
		"innodb_flush_log_at_trx_commit",
		"innodb_read_io_threads",
		"innodb_thread_concurrency",
		"innodb_write_io_threads",
		"innodb_io_capacity",
		"slow_query_log",
		"log_slave_updates",
		"max_allowed_packet",
		"server_id",
		"default_time_zone",
		"time_zone",
		"slave_exec_mode",
		"long_query_time",
		"slave_parallel_type",
		"slave_parallel_workers",
		"sync_binlog",
		"binlog_rows_query_log_events",
		"event_scheduler",
		"eq_range_index_dive_limit",
		"table_open_cache",
		"innodb_open_files",
		"log_bin_compress",
		"loose_log_bin_compress",
		"default_authentication_plugin",
		"gtid_mode",
		"spider_read_only",
		"spider_net_read_timeout",
		"spider_net_write_timeout",
		"sql_mode",
	}
}

// Checker TODO
type Checker struct {
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {
	var cnfFile string
	if config.MonitorConfig.Port == 3306 {
		cnfFile = "/etc/my.cnf.3306"
		if _, err := os.Stat(cnfFile); os.IsNotExist(err) {
			cnfFile = "/etc/my.cnf"
		}
	} else {
		cnfFile = fmt.Sprintf("/etc/my.cnf.%d", config.MonitorConfig.Port)
	}

	diffCmd := exec.Command(
		filepath.Join(filepath.Dir(executable), "pt-config-diff"),
		"--no-version-check",
		"--json-report",
		cnfFile,
		fmt.Sprintf(
			`h=%s,P=%d,u=%s,p=%s`,
			config.MonitorConfig.Ip,
			config.MonitorConfig.Port,
			config.MonitorConfig.Auth.Mysql.User,
			config.MonitorConfig.Auth.Mysql.Password,
		),
	)

	var stdout, stderr bytes.Buffer
	diffCmd.Stdout = &stdout
	diffCmd.Stderr = &stderr

	err = diffCmd.Run()
	if err == nil {
		return "", nil
	}

	var exitError *exec.ExitError
	var ok bool
	if ok = errors.As(err, &exitError); !ok {
		slog.Error("compare mysql config", slog.String("error", err.Error()))
		return "", err
	}

	if exitError.ExitCode() != 1 {
		unexpectErr := errors.Errorf("unexpect error: %s, stderr: %s", err.Error(), stderr.String())
		slog.Error("compare mysql config", slog.String("error", unexpectErr.Error()))
		return "", unexpectErr
	}

	diffs := make(map[string]map[string]interface{})
	jerr := json.Unmarshal(stdout.Bytes(), &diffs)
	if jerr != nil {
		slog.Error("unmarshal variables diffs", slog.String("error", err.Error()))
		return "", jerr
	}

	var res []string
	for variableName, detail := range diffs {
		if slices.Index(importantVariables, variableName) < 0 {
			continue
		}

		var runtimeValue string
		var cnfValue string
		for k, v := range detail {
			if k == cnfFile {
				cnfValue = v.(string)
			} else {
				runtimeValue = v.(string)
			}
		}
		res = append(
			res,
			fmt.Sprintf(
				"[%s] runtime='%s', cnf='%s'",
				variableName, runtimeValue, cnfValue,
			),
		)

	}
	return strings.Join(res, "\n"), nil
}

// Name TODO
func (c *Checker) Name() string {
	return name
}

// New TODO
func New(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{}
}

// Register TODO
func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, New
}
