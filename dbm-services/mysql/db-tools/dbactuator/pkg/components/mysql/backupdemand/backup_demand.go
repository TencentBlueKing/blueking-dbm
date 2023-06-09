// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package backupdemand

import (
	"bufio"
	"encoding/json"
	"fmt"
	"math/rand"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"bk-dbconfig/pkg/core/logger"

	"gopkg.in/ini.v1"

	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
)

type Component struct {
	Params  *Parma `json:"extend"`
	tools   *tools.ToolSet
	context `json:"-"`
}

type Parma struct {
	Host            string   `json:"host" validate:"required,ip"`
	Port            int      `json:"port" validate:"required,gte=3306,lt=65535"`
	BackupType      string   `json:"backup_type" validate:"required"`
	BackupGSD       []string `json:"backup_gsd" validate:"required"` // [grant, schema, data]
	Regex           string   `json:"regex"`
	BackupId        string   `json:"backup_id" validate:"required"`
	BillId          string   `json:"bill_id" validate:"required"`
	CustomBackupDir string   `json:"custom_backup_dir"`
}

type context struct {
	backupConfigPath string
	now              time.Time
	randString       string
	resultReportPath string
	statusReportPath string
}

type Report struct {
	Result []*dbareport.BackupResult `json:"report_result"`
	Status *dbareport.BackupStatus   `json:"report_status"`
}

func (c *Component) Init() (err error) {
	c.tools, err = tools.NewToolSetWithPick(tools.ToolDbbackupGo)
	if err != nil {
		logger.Error("init toolset failed: %s", err.Error())
		return err
	}

	c.now = time.Now()
	rand.Seed(c.now.UnixNano())
	c.randString = fmt.Sprintf("%d%d", c.now.UnixNano(), rand.Intn(100))

	c.backupConfigPath = filepath.Join(
		cst.BK_PKG_INSTALL_PATH,
		fmt.Sprintf("dbactuator-%s", c.Params.BillId),
		fmt.Sprintf("dbbackup.%d.%s.ini", c.Params.Port, c.randString),
	)

	return nil
}

func (c *Component) GenerateBackupConfig() error {
	dailyBackupConfigPath := filepath.Join(
		cst.DbbackupGoInstallPath,
		fmt.Sprintf("dbbackup.%d.ini", c.Params.Port),
	)

	dailyBackupConfigFile, err := ini.LoadSources(ini.LoadOptions{
		PreserveSurroundedQuote: true,
		IgnoreInlineComment:     true,
		AllowBooleanKeys:        true,
		AllowShadows:            true,
	}, dailyBackupConfigPath)
	if err != nil {
		logger.Error("load %s failed: %s", dailyBackupConfigPath, err.Error())
		return err
	}

	var backupConfig config.BackupConfig
	err = dailyBackupConfigFile.MapTo(&backupConfig)
	if err != nil {
		logger.Error("map %s to struct failed: %s", dailyBackupConfigPath, err.Error())
		return err
	}

	backupConfig.Public.BackupType = c.Params.BackupType
	backupConfig.Public.BackupTimeOut = ""
	backupConfig.Public.BillId = c.Params.BillId
	backupConfig.Public.BackupId = c.Params.BackupId
	backupConfig.Public.DataSchemaGrant = strings.Join(c.Params.BackupGSD, ",")

	backupConfig.LogicalBackup.Regex = ""
	if c.Params.BackupType == "logical" {
		backupConfig.LogicalBackup.Regex = c.Params.Regex
	}

	if c.Params.CustomBackupDir != "" {
		backupConfig.Public.BackupDir = filepath.Join(
			backupConfig.Public.BackupDir,
			fmt.Sprintf("%s_%s_%s",
				c.Params.CustomBackupDir,
				c.now.Format("20060102_150405"),
				c.randString))

		err := os.Mkdir(backupConfig.Public.BackupDir, 0755)
		if err != nil {
			logger.Error("mkdir %s failed: %s", backupConfig.Public.BackupDir, err.Error())
			return err
		}
	}

	backupConfigFile := ini.Empty()
	err = backupConfigFile.ReflectFrom(&backupConfig)
	if err != nil {
		logger.Error("reflect backup config failed: %s", err.Error())
		return err
	}

	err = backupConfigFile.SaveTo(c.backupConfigPath)
	if err != nil {
		logger.Error("write backup config to %s failed: %s",
			c.backupConfigPath, err.Error())
		return err
	}

	c.resultReportPath = filepath.Join(
		backupConfig.Public.ResultReportPath,
		fmt.Sprintf("dbareport_result_%d.log", c.Params.Port),
	)
	c.statusReportPath = filepath.Join(
		backupConfig.Public.StatusReportPath,
		fmt.Sprintf("dbareport_status_%d.log", c.Params.Port),
	)

	return nil
}

func (c *Component) DoBackup() error {
	cmd := exec.Command(c.tools.MustGet(tools.ToolDbbackupGo), []string{
		"dumpbackup",
		"--config", c.backupConfigPath,
	}...)

	logger.Info("backup command: %s", cmd)
	err := cmd.Run()
	if err != nil {
		logger.Error("execute %s failed: %s", cmd, err.Error())
		return err
	}
	logger.Info("backup success")
	return nil
}

func (c *Component) generateReport() (report *Report, err error) {
	report = &Report{}

	statusLogFile, err := os.Open(c.statusReportPath)
	if err != nil {
		logger.Error(err.Error())
		return nil, err
	}
	defer func() {
		_ = statusLogFile.Close()
	}()

	thisBillFlag := fmt.Sprintf(`"bill_id":"%s"`, c.Params.BillId)

	var thisBillLatestStatus dbareport.BackupStatus
	var thisBillLatestStatusLine string
	scanner := bufio.NewScanner(statusLogFile)
	for scanner.Scan() {
		if err := scanner.Err(); err != nil {
			logger.Error("scan status report failed: %s", err.Error())
			return nil, err
		}
		line := scanner.Text()
		if strings.Contains(line, thisBillFlag) {
			thisBillLatestStatusLine = line
		}
	}
	err = json.Unmarshal([]byte(thisBillLatestStatusLine), &thisBillLatestStatus)
	if err != nil {
		logger.Error("unmarshal %s failed: %s", thisBillLatestStatusLine, err.Error())
		return nil, err
	}
	logger.Info("backup status: %v", thisBillLatestStatus)

	// ToDo Success 应该是 mysql-dbbackup 的常量
	if thisBillLatestStatus.Status != "Success" {
		err := fmt.Errorf("report status is not Success: %s", thisBillLatestStatusLine)
		logger.Error(err.Error())
		return nil, err
	}
	report.Status = &thisBillLatestStatus

	resultLogFile, err := os.Open(c.resultReportPath)
	if err != nil {
		logger.Error(err.Error())
		return nil, err
	}
	defer func() {
		_ = resultLogFile.Close()
	}()

	scanner = bufio.NewScanner(resultLogFile)
	for scanner.Scan() {
		if err := scanner.Err(); err != nil {
			logger.Error("scan result report failed: %s", err.Error())
			return nil, err
		}
		line := scanner.Text()

		if !strings.Contains(line, thisBillFlag) {
			continue
		}

		var result dbareport.BackupResult
		err = json.Unmarshal([]byte(line), &result)
		if err != nil {
			logger.Error("unmarshal %s failed: %s", line, err.Error())
			return nil, err
		}

		report.Result = append(report.Result, &result)
	}

	return
}

func (c *Component) OutPut() error {
	report, err := c.generateReport()
	if err != nil {
		return err
	}

	err = components.PrintOutputCtx(report)
	if err != nil {
		logger.Error("output backup report failed: %s", err.Error())
		return err
	}
	return nil
}

func (c *Component) Example() interface{} {
	return Component{
		Params: &Parma{
			Host:            "x.x.x.x",
			Port:            20000,
			BackupType:      "logical",
			BackupGSD:       []string{"grant", "schema", "data"},
			Regex:           "",
			BackupId:        "uuid",
			BillId:          "12234",
			CustomBackupDir: "backupDatabaseTable",
		},
	}
}
