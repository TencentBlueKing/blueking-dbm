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
	"io/fs"
	"os"
	"path"
	"path/filepath"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// DbMigrateDumpComp TODO
type DbMigrateDumpComp struct {
	GeneralParam            *components.GeneralParam `json:"general"`
	Params                  DbMigrateDumpParam       `json:"extend"`
	DbMigrateDumpRunTimeCtx `json:"-"`
}

// DbMigrateDumpParam TODO
type DbMigrateDumpParam struct {
	Host            string     `json:"host"  validate:"required,ip"`                // 当前实例的主机地址
	Port            int        `json:"port"  validate:"required,lt=65536,gte=3306"` // 当前实例的端口
	CharSet         string     `json:"charset" validate:"required,checkCharset"`    // 字符集参数 传default过来，按照源数据库的字符集
	RootId          string     `json:"root_id"`
	BkCloudId       int        `json:"bk_cloud_id"`
	DBCloudToken    string     `json:"db_cloud_token"`
	WorkDir         string     `json:"work_dir"`
	DumpDirName     string     `json:"dump_dir_name"` // dump目录名称 {}_schema {}_data
	FileServer      FileServer `json:"fileserver"`
	DbList          []string   `json:"db_list"`
	DataSchemaGrant string     `json:"data_schema_grant"` // all或data,schema:导出数据和库表结构  schema:只导出库表结构
}

// DbMigrateDumpRunTimeCtx TODO
type DbMigrateDumpRunTimeCtx struct {
	backupCmdPath string // 使用备份工具进行dump
	dumpDirPath   string // dump目录绝对路径
	workDirPath   string // schema目录所在的位置 即位于/data/install/mysql_data_migration
}

// Example TODO
func (d *DbMigrateDumpComp) Example() interface{} {
	comp := DbMigrateDumpComp{
		Params: DbMigrateDumpParam{
			Host:    "0.0.0.0",
			Port:    3306,
			CharSet: "default",
			RootId:  "xxxxxxx",
			DbList:  []string{"db1", "db2"},
		},
	}
	return comp
}

// Init TODO
func (d *DbMigrateDumpComp) Init() (err error) {
	/*
		初始化时确定：
		1. 工作目录路径d.workDirPath
		2. 备份文件目录路径d.dumpDirPath
		3. 创建备份目录
	*/
	// 数据迁移工作目录路径
	d.workDirPath = path.Join(cst.BK_PKG_INSTALL_PATH, d.Params.WorkDir)
	// 数据迁移dump文件导出目录路径
	d.dumpDirPath = path.Join(d.workDirPath, d.Params.DumpDirName)
	err = os.MkdirAll(d.dumpDirPath, 0755)
	if err != nil {
		logger.Error("DB克隆目录创建失败！ %s", err.Error())
		return err
	}

	return nil
}

// Precheck TODO
func (d *DbMigrateDumpComp) Precheck() (err error) {
	// 需要确定备份工具是否存在
	d.backupCmdPath = path.Join(cst.MYSQL_TOOL_INSTALL_PATH, cst.BackupDir, "dbbackup")
	if !osutil.FileExist(d.backupCmdPath) {
		return fmt.Errorf("备份工具不存在！目标路径：%s", d.backupCmdPath)
	}
	return
}

// DbMigrateDump TODO
func (d *DbMigrateDumpComp) DbMigrateDump() (err error) {
	sourceDb := strings.Join(d.Params.DbList, ",")
	var dumper mysqlutil.DbbackupDumper
	dumper = &mysqlutil.DbMigrateDumper{
		DumpDir:         d.dumpDirPath,
		DbBackupUser:    d.GeneralParam.RuntimeAccountParam.DbBackupUser,
		DbBackupPwd:     d.GeneralParam.RuntimeAccountParam.DbBackupPwd,
		Ip:              d.Params.Host,
		Port:            d.Params.Port,
		BackupCmdPath:   d.backupCmdPath,
		DbNames:         sourceDb,
		DataSchemaGrant: d.Params.DataSchemaGrant,
		LogDir:          filepath.Join(d.GeneralParam.ActuatorWorkDir(), "logs"),
	}
	if err = dumper.DumpbackupLogical(); err != nil {
		logger.Error("dbbackup dump failed: %s", err.Error())
	}
	return nil
}

// Upload 上传文件到制品库 发现可以机器之间传递文件，目前只要返回待传递文件名称和路径即可
func (d *DbMigrateDumpComp) Upload() (err error) {
	indexFileContent, indexFileName, err := readIndexFile(d.dumpDirPath)
	if err != nil {
		logger.Error("read index file failed! %s", err.Error())
		return err
	}
	var fileList []string
	//indexFileNamePath := path.Join(d.dumpDirPath, indexFileName)
	//fileList = append(fileList, indexFileNamePath)
	fileList = append(fileList, indexFileName)
	for _, tarFile := range indexFileContent.FileList {
		switch tarFile.FileType {
		case "priv":
			continue
		default:
			//tarFilePath := path.Join(d.dumpDirPath, tarFile.FileName)
			fileList = append(fileList, tarFile.FileName)
		}
	}
	info := struct {
		FileNameList []string `json:"file_name_list"`
		FileDirPath  string   `json:"file_dir_path"`
	}{
		FileNameList: fileList,
		FileDirPath:  d.dumpDirPath,
	}
	infoJson, _ := json.Marshal(info)
	returnInfo := components.WrapperOutputString(string(infoJson))
	fmt.Println(returnInfo)
	logger.Info(returnInfo)
	return nil
}

type IndexFileContent struct {
	FileList []TarFileItem `json:"file_list"`
}

type TarFileItem struct {
	FileName string `json:"file_name"`
	FileType string `json:"file_type" enums:"schema,data,metadata,priv"`
}

// getIndexFilePath 用于获取index文件路径
func getIndexFilePath(dumpDirPath string) (indexFileName string, err error) {
	err = filepath.Walk(dumpDirPath, func(path string, info fs.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() && strings.HasSuffix(info.Name(), ".index") {
			indexFileName = info.Name()
			return nil
		}
		return nil
	})
	if err != nil {
		return "", err
	}
	return indexFileName, nil
}

// readIndexFile 读取备份的index文件，获取备份文件信息，用于文件传送
func readIndexFile(indexDirPath string) (content *IndexFileContent, indexFileName string, err error) {
	indexFileName, err = getIndexFilePath(indexDirPath)
	if err != nil {
		return nil, "", err
	}
	indexFilePath := path.Join(indexDirPath, indexFileName)
	data, err := os.ReadFile(indexFilePath)
	if err != nil {
		logger.Error("open file %s failed! %s", indexFilePath, err.Error())
		return nil, "", err
	}
	//var c IndexFileContent
	err = json.Unmarshal(data, &content)
	if err != nil {
		logger.Error(err.Error())
		return nil, "", err
	}

	return content, indexFileName, nil
}
