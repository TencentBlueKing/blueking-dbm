// Package spiderctl TODO
/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */
package spiderctl

import (
	"errors"
	"fmt"
	"os"
	"path"
	"runtime"
	"sync"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// ImportSchemaFromBackendComp import schema from backend to tdbctl component
type ImportSchemaFromBackendComp struct {
	GeneralParam *components.GeneralParam     `json:"general"`
	Params       ImportSchemaFromBackendParam `json:"extend"`
	importSchemaFromBackendRuntime
}

// ImportSchemaFromBackendParam import schema from backend to tdbctl param
type ImportSchemaFromBackendParam struct {
	Host        string `json:"host"  validate:"required,ip"`                        // 当前实例的主机地址
	Port        int    `json:"port"  validate:"required,lt=65536,gte=3306"`         // 当前实例的端口
	BackendHost string `json:"backend_host"  validate:"required,ip"`                // 后端实例的主机地址
	BackendPort int    `json:"backend_port"  validate:"required,lt=65536,gte=3306"` // 后端实例的端口
	SpiderPort  int    `json:"spider_port"  validate:"required,lt=65536,gte=3306"`  // spider节点端口
	UseMydumper bool   `json:"use_mydumper"`                                        // use mydumper
	Stream      bool   `json:"stream"`                                              // mydumper stream myloader stream
	DropBefore  bool   `json:"drop_before"`                                         // 强制覆盖原来的表结构
	Threads     int    `json:"threads"`                                             // 可配置最大并发 for mydumper myloader
	TdbctlUser  string `json:"tdbctl_user" validate:"required"`
	TdbctlPass  string `json:"tdbctl_pass" validate:"required"`
}

type importSchemaFromBackendRuntime struct {
	spiderconn      *native.DbWorker
	tdbctlConn      *native.DbWorker
	charset         string
	dumpDbs         []string
	tmpDumpDir      string
	tmpDumpFile     string
	tdbctlSocket    string
	adminUser       string
	adminPwd        string
	maxThreads      int
	spiderAdminUser string
	spiderAdminPwd  string
}

// Example subcommand example input
func (c *ImportSchemaFromBackendComp) Example() interface{} {
	comp := ImportSchemaFromBackendComp{
		Params: ImportSchemaFromBackendParam{
			Host:        "1.1.1.1",
			Port:        26000,
			SpiderPort:  25000,
			BackendHost: "1.1.1.1",
			BackendPort: 20000,
		},
	}
	return comp
}

// Init prepare run env
func (c *ImportSchemaFromBackendComp) Init() (err error) {
	c.spiderAdminUser = c.Params.TdbctlUser
	c.spiderAdminPwd = c.Params.TdbctlPass
	c.adminUser = c.GeneralParam.RuntimeAccountParam.AdminUser
	c.adminPwd = c.GeneralParam.RuntimeAccountParam.AdminPwd
	c.tdbctlConn, err = native.InsObject{
		Host: c.Params.Host,
		Port: c.Params.Port,
		User: c.adminUser,
		Pwd:  c.adminPwd,
	}.Conn()
	if err != nil {
		logger.Error("Connect tdbctl %d failed:%s", c.Params.Port, err.Error())
		return err
	}

	c.spiderconn, err = native.InsObject{
		Host: c.Params.Host,
		Port: c.Params.SpiderPort,
		User: c.spiderAdminUser,
		Pwd:  c.spiderAdminPwd,
	}.Conn()
	if err != nil {
		logger.Error("Connect spider %d failed:%s", c.Params.Port, err.Error())
		return err
	}
	c.tdbctlSocket, err = c.tdbctlConn.ShowSocket()
	if err != nil {
		logger.Warn("get tdbctl socket failed %s", err.Error())
		err = nil
	}
	alldbs, err := c.spiderconn.ShowDatabases()
	if err != nil {
		logger.Error("show all databases failed:%s", err.Error())
		return err
	}
	version, err := c.spiderconn.SelectVersion()
	if err != nil {
		logger.Error("获取version failed %s", err.Error())
		return err
	}
	finaldbs := util.FilterOutStringSlice(alldbs, computil.GetGcsSystemDatabases(version))
	c.dumpDbs = finaldbs
	c.charset, err = c.spiderconn.ShowServerCharset()
	if err != nil {
		logger.Error("get spider charset failed %s", c.charset)
		return err
	}
	c.tmpDumpDir = path.Join(cst.BK_PKG_INSTALL_PATH, "schema_migrate_"+time.Now().Format(cst.TimeLayoutDir))
	if !cmutil.FileExists(c.tmpDumpDir) {
		stderr, errx := osutil.StandardShellCommand(false, fmt.Sprintf("mkdir %s && chown -R mysql %s", c.tmpDumpDir,
			c.tmpDumpDir))
		if errx != nil {
			logger.Error("init dir %s failed %s,stderr:%s ", c.tmpDumpDir, errx.Error(), stderr)
			return errx
		}
	}
	c.tmpDumpFile = time.Now().Format(cst.TimeLayoutDir) + "_schema.sql"
	if c.Params.Threads > 0 {
		c.maxThreads = c.Params.Threads
	} else {
		c.maxThreads = runtime.NumCPU() / 3
		if c.maxThreads < 1 {
			c.maxThreads = 2
		}
	}
	return err
}

// Migrate do migrate
func (c *ImportSchemaFromBackendComp) Migrate() (err error) {
	switch {
	case c.Params.UseMydumper && c.Params.Stream:
		logger.Info("will use mydumper to stream migrate schema")
		err = c.streamMigrate()
	case c.Params.UseMydumper:
		logger.Info("will use mydumper to migrate schema")
		err = c.migrateUseMydumper()
	default:
		logger.Info("will use mysqldump to migrate schema")
		err = c.migrateUseMysqlDump()
	}
	if err != nil {
		logger.Error("migrate schema failed %s", err.Error())
		return err
	}
	logger.Info("migrate schema success~")
	return nil
}

func (c *ImportSchemaFromBackendComp) streamMigrate() (err error) {
	logger.Info("will create mydumper.cnf ...")
	mydumperCnf := path.Join(c.tmpDumpDir, "mydumper.cnf")
	if !cmutil.FileExists(mydumperCnf) {
		if err = os.WriteFile(mydumperCnf, []byte("[myloader_session_variables]\n	tc_admin=0\n"), 0644); err != nil {
			logger.Error("create mydumper.cnf failed %s", err.Error())
			return err
		}
	}
	logger.Info("create mydumper.cnf success~ ")
	for _, db := range c.dumpDbs {
		streamFlow := mysqlutil.MyStreamDumpLoad{
			Dumper: &mysqlutil.MyDumper{
				Host:    c.Params.BackendHost,
				Port:    c.Params.BackendPort,
				User:    c.Params.TdbctlUser,
				Pwd:     c.Params.TdbctlPass,
				Charset: c.charset,
				Options: mysqlutil.MyDumperOptions{
					Threads:   c.maxThreads,
					NoData:    true,
					UseStream: true,
					Db:        buildBackendDb(db),
				},
			},
			Loader: &mysqlutil.MyLoader{
				Host:    c.Params.Host,
				Port:    c.Params.Port,
				User:    c.adminUser,
				Pwd:     c.adminPwd,
				Charset: c.charset,
				Options: mysqlutil.MyLoaderOptions{
					NoData:         true,
					Threads:        c.maxThreads,
					UseStream:      true,
					DefaultsFile:   mydumperCnf,
					SourceDb:       buildBackendDb(db),
					TargetDb:       db,
					OverWriteTable: c.Params.DropBefore,
				},
			},
		}
		err = streamFlow.Run()
		if err != nil {
			logger.Error("stream migrate %s failed %s", db, err.Error())
			return err
		}
	}
	return nil
}

// migrateUseMydumper 使用mydumper导出数据 myloader 导入
func (c *ImportSchemaFromBackendComp) migrateUseMydumper() (err error) {
	logger.Info("will create mydumper.cnf ...")
	mydumperCnf := path.Join(c.tmpDumpDir, "mydumper.cnf")
	if !cmutil.FileExists(mydumperCnf) {
		if err = os.WriteFile(mydumperCnf, []byte("[myloader_session_variables]\n	tc_admin=0\n"), 0644); err != nil {
			logger.Error("create mydumper.cnf failed %s", err.Error())
			return err
		}
	}
	for _, db := range c.dumpDbs {
		dumper := &mysqlutil.MyDumper{
			Host:    c.Params.BackendHost,
			Port:    c.Params.BackendPort,
			User:    c.Params.TdbctlUser,
			Pwd:     c.Params.TdbctlPass,
			Charset: c.charset,
			DumpDir: c.tmpDumpDir,
			Options: mysqlutil.MyDumperOptions{
				Threads:   c.maxThreads,
				NoData:    true,
				UseStream: false,
				Db:        buildBackendDb(db),
			},
		}
		loader := &mysqlutil.MyLoader{
			Host:        c.Params.Host,
			Port:        c.Params.Port,
			User:        c.adminUser,
			Pwd:         c.adminPwd,
			Charset:     c.charset,
			LoadDataDir: c.tmpDumpDir,
			Options: mysqlutil.MyLoaderOptions{
				NoData:         true,
				Threads:        c.maxThreads,
				UseStream:      false,
				DefaultsFile:   mydumperCnf,
				OverWriteTable: c.Params.DropBefore,
				SourceDb:       buildBackendDb(db),
				TargetDb:       db,
			},
		}
		if err = dumper.Dumper(); err != nil {
			logger.Error("use mydumper dump data failed %s", err.Error())
			return err
		}
		logger.Info("dump data success ~")
		if err = loader.Loader(); err != nil {
			logger.Error("use myloader loader data failed %s", err.Error())
			return err
		}
	}
	return nil
}

// migrateUseMysqlDump 运行备份表结构
// nolint
func (c *ImportSchemaFromBackendComp) migrateUseMysqlDump() (err error) {
	dumpOption := mysqlutil.MySQLDumpOption{
		DumpSchema:              true,
		NoCreateDb:              true,
		NoUseDbAndWirteCreateDb: true,
		AddDropTable:            c.Params.DropBefore,
		// 不用导入后端的存储过程、触发器等
		DumpRoutine: false,
		DumpTrigger: false,
		DumpEvent:   false,
	}

	dumpCommandBinPath := "/home/mysql/dbbackup/mysqldump"
	if !cmutil.FileExists(dumpCommandBinPath) {
		dumpCommandBinPath = path.Join(cst.MysqldInstallPath, "bin", "mysqldump")
	}
	dumper := mysqlutil.MySQLDumper{
		DumpDir:         c.tmpDumpDir,
		Ip:              c.Params.BackendHost,
		Port:            c.Params.BackendPort,
		DbBackupUser:    c.Params.TdbctlUser,
		DbBackupPwd:     c.Params.TdbctlPass,
		DbNames:         buildBackendDbNames(c.dumpDbs),
		DumpCmdFile:     dumpCommandBinPath,
		Charset:         c.charset,
		MySQLDumpOption: dumpOption,
	}
	if err = dumper.Dump(); err != nil {
		logger.Error("dump failed: %s", err.Error())
		return err
	}
	logger.Info("备份表结构成功,开始导入表结构到中控")
	_, err = c.tdbctlConn.Exec("set global tc_admin=0;")
	if err != nil {
		return err
	}
	defer func() {
		_, err = c.tdbctlConn.Exec("set global tc_admin=1;")
		if err != nil {
			logger.Error("set global tc_admin=1 failed %s,请手动配置成tc_admin = 1", err.Error())
		}
	}()
	dumpfileInfo := dumper.GetDumpFileInfo()
	loader := mysqlutil.ExecuteSqlAtLocal{
		IsForce:          false,
		Charset:          c.charset,
		NeedShowWarnings: false,
		Host:             c.Params.Host,
		Port:             c.Params.Port,
		Socket:           c.tdbctlSocket,
		User:             c.GeneralParam.RuntimeAccountParam.AdminUser,
		Password:         c.GeneralParam.RuntimeAccountParam.AdminPwd,
		WorkDir:          c.tmpDumpDir,
	}
	errChan := make(chan error, 1)
	wg := sync.WaitGroup{}
	ctrChan := make(chan struct{}, c.maxThreads)
	for _, db := range c.dumpDbs {
		wg.Add(1)
		ctrChan <- struct{}{}
		dumpfile := dumpfileInfo[buildBackendDb(db)]
		go func(db string, dumpfile string) {
			defer func() { wg.Done(); <-ctrChan }()
			_, err := c.tdbctlConn.Exec(fmt.Sprintf("CREATE DATABASE %s /*!40100 DEFAULT CHARACTER SET %s */;", db, c.charset))
			if err != nil {
				logger.Error("创建数据库:%s 失败:%s", db, err.Error())
				errChan <- err
				return
			}
			err = loader.ExecuteSqlByMySQLClientOne(dumpfile, db, true)
			if err != nil {
				logger.Error("执行导入schema文件:%s 失败:%s", dumpfile, err.Error())
				errChan <- err
			}
		}(db, dumpfile)
	}
	go func() {
		wg.Wait()
		close(errChan)
	}()
	var errs []error
	for err := range errChan {
		errs = append(errs, err)
	}
	return errors.Join(errs...)
}

// MigrateRoutinesAndTriger TODO
func (c *ImportSchemaFromBackendComp) MigrateRoutinesAndTriger() (err error) {
	logger.Info("will import routines and triggers to tdbctl")
	var dumper mysqlutil.Dumper
	dumpOption := mysqlutil.MySQLDumpOption{
		DumpSchema:   false,
		DumpData:     false,
		AddDropTable: c.Params.DropBefore,
		NoCreateTb:   true,
		// 不用导入后端的存储过程、触发器等
		DumpRoutine: true,
		DumpTrigger: true,
		DumpEvent:   true,
	}

	dumper = &mysqlutil.MySQLDumperTogether{
		MySQLDumper: mysqlutil.MySQLDumper{
			DumpDir:         c.tmpDumpDir,
			Ip:              c.Params.Host,
			Port:            c.Params.SpiderPort,
			DbBackupUser:    c.spiderAdminUser,
			DbBackupPwd:     c.spiderAdminPwd,
			DbNames:         c.dumpDbs,
			DumpCmdFile:     path.Join(cst.MysqldInstallPath, "bin", "mysqldump"),
			Charset:         c.charset,
			MySQLDumpOption: dumpOption,
		},
		OutputfileName: c.tmpDumpFile,
	}
	if err = dumper.Dump(); err != nil {
		logger.Error("dump 入存储过程、触发器、event failed: %s", err.Error())
		return err
	}
	err = mysqlutil.ExecuteSqlAtLocal{
		IsForce:          false,
		Charset:          c.charset,
		NeedShowWarnings: false,
		Host:             c.Params.Host,
		Port:             c.Params.Port,
		Socket:           c.tdbctlSocket,
		User:             c.GeneralParam.RuntimeAccountParam.AdminUser,
		Password:         c.GeneralParam.RuntimeAccountParam.AdminPwd,
		WorkDir:          c.tmpDumpDir,
	}.ExecuteSqlByMySQLClientOne(c.tmpDumpFile, "", true)
	if err != nil {
		logger.Error("执行导入存储过程、触发器、event的SQL文件:%s 失败:%s", c.tmpDumpFile, err.Error())
		return err
	}
	return err
}

func buildBackendDbNames(dbs []string) (beDbs []string) {
	for _, db := range dbs {
		beDbs = append(beDbs, buildBackendDb(db))
	}
	return beDbs
}

func buildBackendDb(db string) string {
	return fmt.Sprintf("%s_0", db)
}
