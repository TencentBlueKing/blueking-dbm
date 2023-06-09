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
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/pkg/errors"
	"golang.org/x/exp/slices"
	"golang.org/x/exp/slog"
)

var name = "mysql-config-diff"
var executable string
var importantVariables []string

func init() {
	executable, _ = os.Executable()
	importantVariables = []string{
		"init_connect",
	}
}

// Checker TODO
type Checker struct {
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {
	var cnfFile string
	if config.MonitorConfig.Port == 3306 {
		cnfFile = "/etc/my.cnf"
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
	if exitError, ok = err.(*exec.ExitError); !ok {
		slog.Error("compare mysql config", err)
		return "", err
	}

	if exitError.ExitCode() != 1 {
		unexpectErr := errors.Errorf("unexpect error: %s, stderr: %s", err.Error(), stderr.String())
		slog.Error("compare mysql config", unexpectErr)
		return "", unexpectErr
	}

	diffs := make(map[string]map[string]interface{})
	jerr := json.Unmarshal(stdout.Bytes(), &diffs)
	if jerr != nil {
		slog.Error("unmarshal variables diffs", err)
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
