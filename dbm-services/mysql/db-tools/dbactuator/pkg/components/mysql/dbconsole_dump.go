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
	"archive/zip"
	"errors"
	"fmt"
	"io"
	"os"
	"path"
	"slices"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/db_table_filter"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// DbConsoleDumpComp dbconsole导出组件
type DbConsoleDumpComp struct {
	GeneralParam      *components.GeneralParam `json:"general"`
	Params            DbConsoleDumpParam       `json:"extend"`
	consoleRunTimeCtx `json:"-"`
}

// DbConsoleDumpParam dbconsole 导出参数
type DbConsoleDumpParam struct {
	Host         string              `json:"host"  validate:"required,ip"`                // 当前实例的主机地址
	Port         int                 `json:"port"  validate:"required,lt=65536,gte=3306"` // 当前实例的端口
	CharSet      string              `json:"charset" validate:"required,checkCharset"`    // 字符集参数
	DumpDetail   DbConsoleDumpDetail `json:"dump_detail"`
	UploadDetail UploadBkRepoParam   `json:"upload_detail"`
	// 一个db 一个文件导出
	OneDbOnefile bool   `json:"one_db_one_file"`
	ZipFileName  string `json:"zip_file_name"`
}

// DbConsoleDumpDetail 指定导入对象的参数
type DbConsoleDumpDetail struct {
	Databases []string `json:"databases,omitempty"`
	// 导出指定 tables
	Tables []string `json:"tables,omitempty"`
	// 导出忽略的 tables
	TablesIgnore []string `json:"tables_ignore,omitempty"`
	// 执行dump条件
	Where string `json:"where"`
	// 决定导出数据还是表结构
	DumpData   bool `json:"dump_data"`
	DumpSchema bool `json:"dump_schema"`
}

type consoleRunTimeCtx struct {
	dbs []string // 需要备份的表结构的数据库名称集合
	// 实际备份的表，如果未指定，或者指定未%或者*，则备份全部表
	realTables []string
	// 实际忽略备份的表
	realIgnoreTables []string
	charset          string // 当前实例的字符集
	dumpCmd          string
	isSpider         bool // 是否spider中控
	backupDir        string
}

// Example subcommand example input
func (c *DbConsoleDumpComp) Example() interface{} {
	comp := DbConsoleDumpComp{
		Params: DbConsoleDumpParam{
			Host:    "1.1.1.1",
			Port:    3306,
			CharSet: "default",
			DumpDetail: DbConsoleDumpDetail{
				Databases:    []string{"db1", "db2"},
				Tables:       []string{"tb1", "tb2"},
				TablesIgnore: []string{"igTb1"},
				Where:        "name=foo",
				DumpData:     true,
			},
			UploadDetail: UploadBkRepoParam{
				BackupDir:      "/data1/bak",
				BackupFileName: "test_bak.sql",
			},
		},
	}
	return comp
}

// Init prepare run env
func (c *DbConsoleDumpComp) Init() (err error) {
	var dbTablefiler *db_table_filter.DbTableFilter
	c.realTables = []string{}
	host := c.Params.Host
	port := c.Params.Port
	user := c.GeneralParam.RuntimeAccountParam.AdminUser
	pwd := c.GeneralParam.RuntimeAccountParam.AdminPwd

	// 获取最大可用的磁盘的的目录
	f, err := osutil.GetMostSuitableMountPoint()
	if err != nil {
		logger.Error("获取合适的磁盘失败%v", err)
		return err
	}
	logger.Info("计算的理想磁盘是%v", f)
	rootDir := f.MountPoint

	conn, err := native.InsObject{
		Host: host,
		Port: port,
		User: user,
		Pwd:  pwd,
	}.Conn()

	defer func() {
		if conn != nil {
			conn.Close()
		}
	}()

	version, err := conn.SelectVersion()
	if err != nil {
		logger.Error("get version failed %s", err.Error())
		return err
	}
	sysDbs := computil.GetGcsSystemDatabases(version)
	c.isSpider = strings.Contains(version, "tdbctl")
	tbls := c.Params.DumpDetail.Tables
	if len(tbls) <= 0 {
		tbls = []string{"*"}
	}
	if len(c.Params.DumpDetail.TablesIgnore) <= 0 && !(len(tbls) == 1 && tbls[0] == "*") {
		dbTablefiler, err = db_table_filter.NewFilter(c.Params.DumpDetail.Databases, tbls, nil, nil)
		if err != nil {
			return err
		}

		c.realTables, err = dbTablefiler.GetTablesWithoutDbName(host, port, user, pwd)
		if err != nil {
			return err
		}
	} else if len(c.Params.DumpDetail.TablesIgnore) > 0 {
		ignoreDbs := c.Params.DumpDetail.Databases
		dbTablefiler, err = db_table_filter.NewFilter(
			c.Params.DumpDetail.Databases, tbls,
			ignoreDbs, c.Params.DumpDetail.TablesIgnore,
		)
		if err != nil {
			return err
		}

		c.realTables, err = dbTablefiler.GetTablesWithoutDbName(host, port, user, pwd)
		if err != nil {
			return err
		}

		res, err := dbTablefiler.GetExcludeTables(host, port, user, pwd)
		if err != nil {
			return err
		}
		for k, v := range res {
			for _, tb := range v {
				c.realIgnoreTables = append(c.realIgnoreTables, fmt.Sprintf("%s.%s", k, tb))
			}
		}
	}
	logger.Info("special tables %v", c.realTables)
	logger.Info("ignore tables %v", c.realIgnoreTables)
	// ignore sys dbs
	c.dbs = slices.DeleteFunc(c.Params.DumpDetail.Databases, func(s string) bool {
		return slices.Contains(sysDbs, s)
	})
	if len(c.dbs) <= 0 {
		return fmt.Errorf("not found any databases need to dump")
	}
	// check database exist
	realDbs, err := conn.ShowDatabases()
	if err != nil {
		return err
	}

	for _, db := range c.dbs {
		var errs []error
		if !slices.Contains(realDbs, db) {
			errs = append(errs, fmt.Errorf("%s not found \n", db))
		}
		if len(errs) >= 1 {
			return errors.Join(errs...)
		}
	}

	c.charset = strings.TrimSpace(c.Params.CharSet)
	if slices.Contains([]string{"default", ""}, strings.ToLower(c.charset)) {
		if c.charset, err = conn.ShowServerCharset(); err != nil {
			logger.Error("failed to obtain the character set of the instance%s", err.Error())
			return err
		}
	}
	c.dumpCmd = path.Join(cst.MysqldInstallPath, "bin", "mysqldump")
	// to export the table structure from the central control
	// you need to use the mysqldump that comes with the central control
	if c.isSpider {
		c.dumpCmd = path.Join(cst.TdbctlInstallPath, "bin", "mysqldump")
	}
	c.backupDir = path.Join(rootDir, "dbm_console_dump")
	if !osutil.FileExist(c.backupDir) {
		logger.Warn("backupdir: %s不存在", c.backupDir)
		stdOut, err := osutil.StandardShellCommand(false, fmt.Sprintf("mkdir -p %s && chown mysql:mysql %s",
			c.backupDir, c.backupDir))
		if err != nil {
			return fmt.Errorf("mkdir %s failed,stdout:%s,err:%w", c.backupDir, stdOut, err)
		}
	}
	return err
}

// Run Command Run
func (c *DbConsoleDumpComp) Run() (err error) {
	logger.Info("start dumping ... ")
	var dumper mysqlutil.Dumper
	backupfiles := []string{}

	dumpOption := mysqlutil.MySQLDumpOption{
		DumpSchema:     c.Params.DumpDetail.DumpSchema,
		DumpData:       c.Params.DumpDetail.DumpData,
		AddDropTable:   true,
		DumpRoutine:    true,
		DumpTrigger:    true,
		DumpEvent:      true,
		ExtendedInsert: true,
	}

	if c.isSpider {
		dumpOption.GtidPurgedOff = true
	}

	if len(c.realTables) > 0 && len(c.dbs) > 1 {
		err = fmt.Errorf("mysqldump only support one database if --tables not empty")
		logger.Error(err.Error())
		return err
	}

	dumper = mysqlutil.MySQLDumper{
		DumpDir:         c.backupDir,
		Ip:              c.Params.Host,
		Port:            c.Params.Port,
		DbBackupUser:    c.GeneralParam.RuntimeAccountParam.AdminUser,
		DbBackupPwd:     c.GeneralParam.RuntimeAccountParam.AdminPwd,
		DbNames:         c.dbs,
		Tables:          c.realTables,
		IgnoreTables:    c.realIgnoreTables,
		Where:           c.Params.DumpDetail.Where,
		DumpCmdFile:     c.dumpCmd,
		Charset:         c.charset,
		MySQLDumpOption: dumpOption,
	}

	for _, db := range c.dbs {
		backupfiles = append(backupfiles, fmt.Sprintf("%s.sql", db))
	}

	if err = dumper.Dump(); err != nil {
		logger.Error("dump failed: %s", err.Error())
		return err
	}
	// 打包文件
	if err = zipFiles(c.backupDir, backupfiles, c.Params.ZipFileName); err != nil {
		logger.Error("failed to compress packaged file%v", err)
		return err
	}
	logger.Info("compression and packaging file successfully")
	return err
}

// Upload upload to bk repo
func (c *DbConsoleDumpComp) Upload() (err error) {
	// 如果是按照db分文件导出的需要打包成tar包
	logger.Info("start uploading...")
	up := c.Params.UploadDetail
	up.BackupFileName = c.Params.ZipFileName
	up.BackupDir = c.backupDir
	return up.Upload()
}

func zipFiles(pathDir string, filesToZip []string, zipFileName string) error {
	zipFile, err := os.Create(path.Join(pathDir, zipFileName))
	if err != nil {
		return err
	}
	defer zipFile.Close()

	zipWriter := zip.NewWriter(zipFile)
	defer zipWriter.Close()

	for _, file := range filesToZip {
		err = addToZip(path.Join(pathDir, file), zipWriter)
		if err != nil {
			return err
		}
	}

	return nil
}

func addToZip(filename string, zipWriter *zip.Writer) error {
	file, err := os.Open(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	info, err := file.Stat()
	if err != nil {
		return err
	}

	header, err := zip.FileInfoHeader(info)
	if err != nil {
		return err
	}

	header.Name = info.Name()
	header.Method = zip.Deflate

	writer, err := zipWriter.CreateHeader(header)
	if err != nil {
		return err
	}

	_, err = io.Copy(writer, file)
	return err
}
