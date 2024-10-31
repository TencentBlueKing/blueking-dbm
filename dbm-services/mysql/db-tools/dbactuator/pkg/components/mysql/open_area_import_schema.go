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
	"fmt"
	"os"
	"path"
	"regexp"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"

	"github.com/pkg/errors"
)

// OpenAreaImportSchemaComp TODO
type OpenAreaImportSchemaComp struct {
	GeneralParam                   *components.GeneralParam  `json:"general"`
	Params                         OpenAreaImportSchemaParam `json:"extend"`
	OpenAreaImportSchemaRunTimeCtx `json:"-"`
}

// OpenAreaImportSchemaParam TODO
type OpenAreaImportSchemaParam struct {
	Host          string                    `json:"host" validate:"required,ip"`
	Port          int                       `json:"port" validate:"required,lt=65536,gte=3306"`
	CharSet       string                    `json:"charSet" validate:"required,checkCharset"`
	RootId        string                    `json:"root_id"`
	BkCloudId     int                       `json:"bk_cloud_id"`
	WorkDir       string                    `json:"work_dir"`
	DumpDirName   string                    `json:"dump_dir_name"` // dump目录名称 {}_schema {}_data
	DBCloudToken  string                    `json:"db_cloud_token"`
	OpenAreaParam []OneOpenAreaImportSchema `json:"open_area_param"`
}

// OneOpenAreaImportSchema TODO
type OneOpenAreaImportSchema struct {
	Schema string   `json:"schema"` // 指定dump的库的名称
	NewDB  string   `json:"newdb"`  // 开区的新库的名称
	DbList []string `json:"db_list"`
}

// OpenAreaImportSchemaRunTimeCtx TODO
type OpenAreaImportSchemaRunTimeCtx struct {
	charset       string // 当前实例的字符集
	workDir       string
	tarFilePath   string
	md5FilePath   string
	dumpDir       string
	conn          *native.DbWorker
	socket        string
	decompressDir string
}

// Example TODO
func (c *OpenAreaImportSchemaComp) Example() interface{} {
	comp := OpenAreaImportSchemaComp{
		Params: OpenAreaImportSchemaParam{
			Host:    "0.0.0.0",
			Port:    3306,
			CharSet: "default",
			RootId:  "xxxxxxx",
			OpenAreaParam: []OneOpenAreaImportSchema{
				{
					Schema: "data1",
					NewDB:  "data1-1001",
				},
				{
					Schema: "data2",
					NewDB:  "data2-1001",
				},
			},
		},
	}
	return comp
}

// Init TODO
func (c *OpenAreaImportSchemaComp) Init() (err error) {
	// 连接实例，确认字符集
	c.conn, err = native.InsObject{
		Host: c.Params.Host,
		Port: c.Params.Port,
		User: c.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  c.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.Conn()
	if err != nil {
		logger.Error("Connect %d failed:%s", c.Params.Port, err.Error())
		return err
	}
	c.charset = c.Params.CharSet
	if c.Params.CharSet == "default" {
		if c.charset, err = c.conn.ShowServerCharset(); err != nil {
			logger.Error("获取实例的字符集失败：%s", err.Error())
			return err
		}
	}
	c.socket, err = c.conn.ShowSocket()
	if err != nil {
		logger.Error("get socket failed!error:", err.Error())
		return err
	}

	if len(c.Params.WorkDir) > 0 {
		c.workDir = path.Join(cst.BK_PKG_INSTALL_PATH, c.Params.WorkDir)
	} else {
		c.workDir = path.Join(cst.BK_PKG_INSTALL_PATH, "mysql_open_area")
	}
	// 绝对路径
	tarFileName := fmt.Sprintf("%s.tar.gz", c.Params.DumpDirName)
	c.tarFilePath = path.Join(c.workDir, tarFileName)
	md5FileName := fmt.Sprintf("%s.md5sum", c.Params.DumpDirName)
	c.md5FilePath = path.Join(c.workDir, md5FileName)
	// 避免并发时共用文件导致导入错误，同一机器上的不同实例使用自己的解压目录
	c.decompressDir = path.Join(c.workDir, fmt.Sprintf("%s_%d", c.Params.Host, c.Params.Port))
	err = os.MkdirAll(c.decompressDir, 0755)
	if err != nil {
		logger.Error("解压目录创建失败：%s", err.Error())
		return err
	}
	c.dumpDir = path.Join(c.decompressDir, c.Params.DumpDirName)
	return
}

// Precheck TODO
func (c *OpenAreaImportSchemaComp) Precheck() (err error) {
	if !util.FileExists(c.tarFilePath) {
		logger.Error("tar file(*s) does not exist.", c.tarFilePath)
		return errors.New("压缩文件不存在")
	}
	if !util.FileExists(c.md5FilePath) {
		logger.Error("tar file(*s) does not exist.", c.tarFilePath)
		return errors.New("md5sum文件不存在")
	}
	return
}

// DecompressDumpDir TODO
func (c *OpenAreaImportSchemaComp) DecompressDumpDir() (err error) {
	md5Byte, err := os.ReadFile(c.md5FilePath)
	if err != nil {
		logger.Error("read md5sum(%s) file got an error:%s", c.md5FilePath, err.Error())
		return err
	}
	realMd5sumVal, err := osutil.GetFileMd5(c.tarFilePath)
	if err != nil {
		logger.Error("get real md5sum value failed!")
		return err
	}
	sourceMd5sumVal := string(md5Byte)
	if sourceMd5sumVal != realMd5sumVal {
		msg := fmt.Sprintf("realMD5Sum(%s) is not equal to md5sum(%s) recored in the file(%s)",
			realMd5sumVal, sourceMd5sumVal, c.md5FilePath)
		logger.Error(msg)
		return errors.New(msg)
	}
	logger.Info("get tar file sucess!")
	decopressCmd := fmt.Sprintf("tar -zxf %s -C %s", c.tarFilePath, c.decompressDir)
	output, err := osutil.ExecShellCommand(false, decopressCmd)
	if err != nil {
		logger.Error("execute(%s) get an error:%s,%s", decopressCmd, output, err.Error())
		return err
	}

	return
}

// EraseAutoIncrement TODO
func (c *OpenAreaImportSchemaComp) EraseAutoIncrement() (err error) {
	for _, oneSchemaInfo := range c.Params.OpenAreaParam {
		schemaFilePath := fmt.Sprintf("%s/%s.sql", c.dumpDir, oneSchemaInfo.Schema)
		schemaContent, err := os.ReadFile(schemaFilePath)
		if err != nil {
			logger.Error("read file(%s) got an error:%s", schemaFilePath, err.Error())
			return err
		}
		reg, err := regexp.Compile(`(?i)AUTO_INCREMENT=(\d+)`)
		if err != nil {
			logger.Error("regexp.Compile failed:%s", err.Error())
			return err
		}
		newSchemaContent := reg.ReplaceAllString(string(schemaContent), "")
		newSchemaFilePath := fmt.Sprintf("%s.%s.new", schemaFilePath, oneSchemaInfo.NewDB)

		f, err := os.Create(newSchemaFilePath)
		if err != nil {
			logger.Error("create file(%s) error:%s", newSchemaFilePath, err.Error())
			return err
		}
		_, err = f.WriteString(newSchemaContent)
		if err != nil {
			logger.Error("write file(%s) error:%s", newSchemaFilePath, err.Error())
			return err
		}
	}
	return nil
}

// CreateNewDatabase TODO
func (c *OpenAreaImportSchemaComp) CreateNewDatabase() (err error) {
	for _, oneShemaInfo := range c.Params.OpenAreaParam {
		createDBSql := fmt.Sprintf("create database if not exists `%s` charset %s;",
			oneShemaInfo.NewDB, c.charset)
		_, err := c.conn.Exec(createDBSql)
		if err != nil {
			logger.Error("create db %s got an error:%s", oneShemaInfo.NewDB, err.Error())
			return err
		}
	}
	return
}

// CreateDatabase TODO
func (c *OpenAreaImportSchemaComp) CreateDatabase() (err error) {
	// 导出文件有create database语句，这里先创建一次，重复的话报错终止
	for _, oneShemaInfo := range c.Params.OpenAreaParam {
		for _, db := range oneShemaInfo.DbList {
			createDBSql := fmt.Sprintf("create database `%s` charset %s;",
				db, c.charset)
			_, err := c.conn.Exec(createDBSql)
			if err != nil {
				logger.Error("create db %s got an error:%s", db, err.Error())
				return err
			}
		}

	}
	return
}

// OpenAreaImportSchema TODO
func (c *OpenAreaImportSchemaComp) OpenAreaImportSchema() (err error) {
	for _, oneSchemaInfo := range c.Params.OpenAreaParam {
		schemaName := fmt.Sprintf("%s.sql.%s.new", oneSchemaInfo.Schema, oneSchemaInfo.NewDB)
		err = mysqlutil.ExecuteSqlAtLocal{
			IsForce:          false,
			Charset:          c.charset,
			NeedShowWarnings: false,
			Host:             c.Params.Host,
			Port:             c.Params.Port,
			Socket:           c.socket,
			WorkDir:          c.dumpDir,
			User:             c.GeneralParam.RuntimeAccountParam.AdminUser,
			Password:         c.GeneralParam.RuntimeAccountParam.AdminPwd,
		}.MyExecuteSqlByMySQLClientOne(schemaName, oneSchemaInfo.NewDB)
		if err != nil {
			logger.Error("执行%s文件失败！", schemaName)
			return err
		}
	}
	return nil
}

// OpenAreaImportData TODO
func (c *OpenAreaImportSchemaComp) OpenAreaImportData() (err error) {
	for _, oneShemaInfo := range c.Params.OpenAreaParam {
		dataFileName := fmt.Sprintf("%s.sql", oneShemaInfo.Schema)
		err = mysqlutil.ExecuteSqlAtLocal{
			IsForce:          false,
			Charset:          c.charset,
			NeedShowWarnings: false,
			Host:             c.Params.Host,
			Port:             c.Params.Port,
			Socket:           c.socket,
			WorkDir:          c.dumpDir,
			User:             c.GeneralParam.RuntimeAccountParam.AdminUser,
			Password:         c.GeneralParam.RuntimeAccountParam.AdminPwd,
		}.MyExecuteSqlByMySQLClientOne(dataFileName, oneShemaInfo.NewDB)
		if err != nil {
			logger.Error("执行%s文件失败！", dataFileName)
			return err
		}
	}
	return nil
}

// MysqlDataMigrateImport TODO
func (c *OpenAreaImportSchemaComp) MysqlDataMigrateImport() (err error) {
	for _, oneShemaInfo := range c.Params.OpenAreaParam {
		for _, db := range oneShemaInfo.DbList {
			dataFileName := fmt.Sprintf("%s.sql", db)
			err = mysqlutil.ExecuteSqlAtLocal{
				IsForce:          false,
				Charset:          c.charset,
				NeedShowWarnings: false,
				Host:             c.Params.Host,
				Port:             c.Params.Port,
				Socket:           c.socket,
				WorkDir:          c.dumpDir,
				User:             c.GeneralParam.RuntimeAccountParam.AdminUser,
				Password:         c.GeneralParam.RuntimeAccountParam.AdminPwd,
			}.MyExecuteSqlByMySQLClientOne(dataFileName, db)
			if err != nil {
				logger.Error("执行%s文件失败！", dataFileName)
				return err
			}
		}

	}
	return nil
}

// CleanDumpDir TODO
func (c *OpenAreaImportSchemaComp) CleanDumpDir() (err error) {
	return
}
