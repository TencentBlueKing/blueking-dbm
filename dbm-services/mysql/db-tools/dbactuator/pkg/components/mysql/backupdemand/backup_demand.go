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
	"path/filepath"
	"strings"
	"time"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/mysqlcomm"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"

	"gopkg.in/ini.v1"

	"dbm-services/common/go-pubpkg/logger"
)

type Component struct {
	Params  *Param `json:"extend"`
	tools   *tools.ToolSet
	context `json:"-"`
}

type Param struct {
	Host            string   `json:"host" validate:"required,ip"`
	Port            int      `json:"port" validate:"required,gte=3306,lt=65535"`
	Role            string   `json:"role" validate:"required"`
	ShardID         int      `json:"shard_id"`
	BackupType      string   `json:"backup_type" validate:"required"`
	BackupGSD       []string `json:"backup_gsd" validate:"required"` // [grant, schema, data]
	Regex           string   `json:"regex"`
	BackupId        string   `json:"backup_id" validate:"required"`
	BillId          string   `json:"bill_id" validate:"required"`
	CustomBackupDir string   `json:"custom_backup_dir"`
}

type context struct {
	backupConfigPaths map[int]string
	now               time.Time
	randString        string
	//resultReportPath  string
	statusReportPath string
	reportPath       string
	backupPort       []int  // 当在 spider master备份时, 会有 [25000, 26000] 两个端口
	backupDir        string //只是兼容tbinlogdumper的备份日志输出，存储备份目录信息，没有任何处理逻辑
}

type Report struct {
	Result *dbareport.IndexContent `json:"report_result"`
	Status *dbareport.BackupStatus `json:"report_status"`
}

func (c *Component) Init() (err error) {
	c.Params.Role = strings.ToUpper(c.Params.Role)

	c.tools, err = tools.NewToolSetWithPick(tools.ToolDbbackupGo)
	if err != nil {
		logger.Error("init toolset failed: %s", err.Error())
		return err
	}

	c.now = time.Now()
	rand.Seed(c.now.UnixNano())
	c.randString = fmt.Sprintf("%d%d", c.now.UnixNano(), rand.Intn(100))

	c.backupConfigPaths = make(map[int]string)

	c.backupPort = append(c.backupPort, c.Params.Port)
	c.backupConfigPaths[c.Params.Port] = filepath.Join(
		cst.BK_PKG_INSTALL_PATH,
		fmt.Sprintf("dbactuator-%s", c.Params.BillId),
		fmt.Sprintf("dbbackup.%d.%s.ini", c.Params.Port, c.randString),
	)

	if c.Params.Role == cst.BackupRoleSpiderMaster {
		tdbctlPort := mysqlcomm.GetTdbctlPortBySpider(c.Params.Port)
		c.backupPort = append(c.backupPort, tdbctlPort)

		c.backupConfigPaths[tdbctlPort] = filepath.Join(
			cst.BK_PKG_INSTALL_PATH,
			fmt.Sprintf("dbactuator-%s", c.Params.BillId),
			fmt.Sprintf("dbbackup.%d.%s.ini", tdbctlPort, c.randString),
		)
	}

	return nil
}

func (c *Component) GenerateBackupConfig() error {
	for _, port := range c.backupPort {
		dailyBackupConfigPath := filepath.Join(
			cst.DbbackupGoInstallPath,
			fmt.Sprintf("dbbackup.%d.ini", port),
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
		backupConfig.Public.ShardValue = c.Params.ShardID

		backupConfig.LogicalBackup.Regex = ""
		if c.Params.BackupType == "logical" {
			backupConfig.LogicalBackup.Regex = c.Params.Regex
		}

		if c.Params.CustomBackupDir != "" {
			backupConfig.Public.BackupDir = filepath.Join(
				backupConfig.Public.BackupDir,
				fmt.Sprintf("%s_%s_%d_%s",
					c.Params.CustomBackupDir,
					c.now.Format("20060102150405"),
					port,
					c.randString))

			err := os.Mkdir(backupConfig.Public.BackupDir, 0755)
			if err != nil {
				logger.Error("mkdir %s failed: %s", backupConfig.Public.BackupDir, err.Error())
				return err
			}

		}
		// 增加为tbinlogdumper做库表备份的日志输出，保存流程上下文
		c.backupDir = backupConfig.Public.BackupDir

		backupConfigFile := ini.Empty()
		err = backupConfigFile.ReflectFrom(&backupConfig)
		if err != nil {
			logger.Error("reflect backup config failed: %s", err.Error())
			return err
		}

		backupConfigPath := c.backupConfigPaths[port]
		err = backupConfigFile.SaveTo(backupConfigPath)
		if err != nil {
			logger.Error("write backup config to %s failed: %s",
				backupConfigPath, err.Error())
			return err
		}

		c.statusReportPath = filepath.Join(
			backupConfig.Public.StatusReportPath,
			fmt.Sprintf("dbareport_status_%d.log", c.Params.Port),
		)
	}

	return nil
}

func (c *Component) DoBackup() error {
	for _, port := range c.backupPort {
		backupConfigPath := c.backupConfigPaths[port]
		cmdArgs := []string{c.tools.MustGet(tools.ToolDbbackupGo), "dumpbackup", "--config", backupConfigPath}
		logger.Info("backup command: %s", strings.Join(cmdArgs, " "))

		_, errStr, err := cmutil.ExecCommand(false, "",
			cmdArgs[0], cmdArgs[1:]...)

		if err != nil {
			logger.Error("execute %s failed: %s, msg:%s", cmdArgs, err.Error(), errStr)
			return err
		}
		logger.Info("backup success with %s", backupConfigPath)
	}
	return nil
}

func (c *Component) generateReport() (report *Report, indexFile string, err error) {
	report = &Report{}

	indexFileSearch := filepath.Join(c.backupDir, "*.index")
	if files, err := filepath.Glob(indexFileSearch); err != nil {
		return nil, indexFile, err
	} else {
		for _, f := range files {
			indexContent, err := os.ReadFile(f)
			if err != nil {
				return nil, indexFile, err
			}
			var result dbareport.IndexContent
			err = json.Unmarshal(indexContent, &result)
			if err != nil {
				logger.Error("unmarshal file %s failed: %s", f, err.Error())
				continue
				//return nil, err
			}
			if result.BillId == c.Params.BillId && c.Params.BillId != "" {
				report.Result = &result
				indexFile = f
				break
			}
		}
	}
	if report.Result == nil {
		return nil, indexFile, errors.Errorf("backup index file not found for %d", c.backupPort)
	}

	statusLogFile, err := os.Open(c.statusReportPath)
	if err != nil {
		logger.Error(err.Error())
		return nil, indexFile, err
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
			return nil, indexFile, err
		}
		line := scanner.Text()
		if strings.Contains(line, thisBillFlag) {
			thisBillLatestStatusLine = line
		}
	}
	err = json.Unmarshal([]byte(thisBillLatestStatusLine), &thisBillLatestStatus)
	if err != nil {
		logger.Error("unmarshal %s failed: %s", thisBillLatestStatusLine, err.Error())
		return nil, indexFile, err
	}
	logger.Info("backup status: %v", thisBillLatestStatus)

	// ToDo Success 应该是 mysql-dbbackup 的常量
	if thisBillLatestStatus.Status != "Success" {
		err := fmt.Errorf("report status is not Success: %s", thisBillLatestStatusLine)
		logger.Error(err.Error())
		return nil, indexFile, err
	}
	report.Status = &thisBillLatestStatus
	return
}

func (c *Component) OutPut() error {
	report, _, err := c.generateReport()
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
		Params: &Param{
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

// OutPutForTBinlogDumper 增加为tbinlogdumper做库表备份的日志输出，保存流程上下文
func (c *Component) OutPutForTBinlogDumper() error {
	ret := make(map[string]interface{})
	report, indexFile, err := c.generateReport()
	if err != nil {
		return err
	}
	ret["report_result"] = report.Result
	ret["report_status"] = report.Status
	ret["backup_dir"] = c.backupDir
	ret["backup_index"] = indexFile

	err = components.PrintOutputCtx(ret)
	if err != nil {
		logger.Error("output backup report failed: %s", err.Error())
		return err
	}
	return nil
}
