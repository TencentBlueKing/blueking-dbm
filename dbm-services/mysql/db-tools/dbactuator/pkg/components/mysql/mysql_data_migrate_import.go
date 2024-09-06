/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mysql

import (
	"encoding/json"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"strings"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

type DbMigrateImportComp struct {
	GeneralParam              *components.GeneralParam `json:"general"`
	Params                    DbMigrateImportParam     `json:"extend"`
	DbMigrateImportRunTimeCtx `json:"-"`
}

type DbMigrateImportParam struct {
	Host          string `json:"host"`
	Port          int    `json:"port"`
	CharSet       string `json:"charset"`
	RootId        string `json:"root_id"`
	BkCloudId     int    `json:"bk_cloud_id"`
	WorkDir       string `json:"work_dir"` // 数据迁移工作的目录名称 mysql_data_migration
	ImportDirName string `json:"import_dir_name"`
	IndexFileName string `json:"index_file_name"`
	LogDir        string `json:"-"`
}

type DbMigrateImportRunTimeCtx struct {
	backupCmdPath     string            // 备份工具路径
	importDirPath     string            // 下发的压缩文件路径
	workDirPath       string            // 数据迁移工作路径
	indexFilePath     string            // index文件路径
	targetDir         string            // 解压文件的目标路径 目前和importDirPath一致
	dmBackupIndexFile DmBackupIndexFile // index文件获取的信息
	unTarDirName      string            // 解压文件后的目录名称
	unTarDirPath      string            // 解压后的目录位置
}

type DmBackupIndexFile struct {
	FileList []FileListInfo `json:"file_list"`
}

type FileListInfo struct {
	FileName string `json:"file_name"`
	FileType string `json:"file_type"`
}

func (d *DbMigrateImportComp) Example() interface{} {
	comp := DbMigrateImportComp{
		Params: DbMigrateImportParam{
			Host:          "0.0.0.0",
			Port:          3306,
			CharSet:       "default",
			RootId:        "xxxxxxx",
			WorkDir:       "/data/install/mysql_data_migration/",
			ImportDirName: "xxxxxxx",
		},
	}
	return comp
}

func (d *DbMigrateImportComp) Init() (err error) {
	// 拼接工作目录和备份所在目录路径
	d.workDirPath = path.Join(cst.BK_PKG_INSTALL_PATH, d.Params.WorkDir)
	d.importDirPath = path.Join(d.workDirPath, d.Params.ImportDirName)
	d.indexFilePath = path.Join(d.importDirPath, d.Params.IndexFileName)
	if _, err := os.Stat(d.indexFilePath); os.IsNotExist(err) {
		return fmt.Errorf("index file %s does not exist: %s", d.importDirPath, err.Error())
	}
	d.Params.LogDir = filepath.Join(d.GeneralParam.ActuatorWorkDir(), "logs")
	return nil
}

func (d *DbMigrateImportComp) Precheck() (err error) {
	d.backupCmdPath = path.Join(cst.MYSQL_TOOL_INSTALL_PATH, cst.BackupDir, "dbbackup")
	if !osutil.FileExist(d.backupCmdPath) {
		return fmt.Errorf("备份工具不存在！目标路径：%s", d.backupCmdPath)
	}
	return nil
}

// DecompressDumpDir 解压备份目录
func (d *DbMigrateImportComp) DecompressDumpDir() (err error) {
	// 读取index文件，获取待解压文件信息
	err = d.IndexFileParse()
	if err != nil {
		return err
	}
	// 解压
	err = d.UntarFiles()
	if err != nil {
		return err
	}

	return nil
}

// DbMigrateImport 数据导入
func (d *DbMigrateImportComp) DbMigrateImport() (err error) {
	loadCmd := d.GetLoadCmd()
	logger.Info("loadbackup cmd is :%s", loadCmd)
	if output, err := osutil.StandardShellCommand(false, loadCmd); err != nil {
		return fmt.Errorf("execte %s get an error:%s,%w", loadCmd, output, err)
	}
	return nil
}

// IndexFileParse 解析index文件，获取备份文件信息
func (d *DbMigrateImportComp) IndexFileParse() (err error) {
	data, err := os.ReadFile(d.indexFilePath)
	if err != nil {
		return err
	}
	err = json.Unmarshal(data, &d.dmBackupIndexFile)
	if err != nil {
		return err
	}
	return nil
}

// UntarFiles 解压
func (d *DbMigrateImportComp) UntarFiles() (err error) {
	if len(d.dmBackupIndexFile.FileList) > 0 {
		for _, tarFile := range d.dmBackupIndexFile.FileList {
			if tarFile.FileType == "tar" {
				cmd := fmt.Sprintf(`cd %s && tar -xf %s -C %s/`,
					d.importDirPath, tarFile.FileName, d.importDirPath)
				if _, err := osutil.ExecShellCommand(false, cmd); err != nil {
					return errors.Wrap(err, cmd)
				}
			}
		}
	} else {
		return errors.New("库表备份文件不存在！")
	}
	d.unTarDirName = strings.TrimSuffix(d.Params.IndexFileName, ".index")
	d.unTarDirPath = path.Join(d.importDirPath, d.unTarDirName)
	return
}

// GetLoadCmd 获取loadbackup命令
func (d *DbMigrateImportComp) GetLoadCmd() string {
	loadCmd := fmt.Sprintf(`cd %s && %s loadbackup logical -u %s -p %s --host %s --port %d %s`, d.importDirPath,
		d.backupCmdPath, d.GeneralParam.RuntimeAccountParam.AdminUser,
		d.GeneralParam.RuntimeAccountParam.AdminPwd, d.Params.Host, d.Params.Port, d.GetLoadCmdOption())
	if d.Params.LogDir != "" {
		loadCmd += fmt.Sprintf(" --log-dir %s", d.Params.LogDir)
	}
	return loadCmd
}

// GetLoadCmdOption 获取loadbackup命令需要参数
func (d *DbMigrateImportComp) GetLoadCmdOption() string {
	opt := fmt.Sprintf(`--load-dir %s -i %s --enable-binlog `, d.unTarDirPath, d.indexFilePath)
	return opt
}
