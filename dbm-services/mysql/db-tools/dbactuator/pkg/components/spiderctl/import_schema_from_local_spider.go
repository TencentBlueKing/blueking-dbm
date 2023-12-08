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
	"fmt"
	"os"
	"path"
	"runtime"
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

// ImportSchemaFromLocalSpiderComp TODO
type ImportSchemaFromLocalSpiderComp struct {
	GeneralParam *components.GeneralParam         `json:"general"`
	Params       ImportSchemaFromLocalSpiderParam `json:"extend"`
	importSchemaFromLocalSpiderRuntime
}

// ImportSchemaFromLocalSpiderParam TODO
type ImportSchemaFromLocalSpiderParam struct {
	Host       string `json:"host"  validate:"required,ip"`                       // 当前实例的主机地址
	Port       int    `json:"port"  validate:"required,lt=65536,gte=3306"`        // 当前实例的端口
	SpiderPort int    `json:"spider_port"  validate:"required,lt=65536,gte=3306"` // spider节点端口
	Stream     bool   `json:"stream"`                                             // mydumper stream myloader stream
	DropBefore bool   `json:"drop_before"`                                        // 强制覆盖原来的表结构
}

type importSchemaFromLocalSpiderRuntime struct {
	spiderconn   *native.DbWorker
	tdbctlConn   *native.DbWorker
	version      string
	charset      string
	dumpDbs      []string
	tmpDumpDir   string
	tmpDumpFile  string
	tdbctlSocket string
	adminUser    string
	adminPwd     string
	maxThreads   int
}

// Example subcommand example input
func (i *ImportSchemaFromLocalSpiderComp) Example() interface{} {
	comp := ImportSchemaFromLocalSpiderComp{
		Params: ImportSchemaFromLocalSpiderParam{
			Host:       "1.1.1.1",
			Port:       26000,
			SpiderPort: 25000,
		},
	}
	return comp
}

// Init prepare run env
func (c *ImportSchemaFromLocalSpiderComp) Init() (err error) {
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
		User: c.adminUser,
		Pwd:  c.adminPwd,
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
	finaldbs := []string{}
	for _, db := range util.FilterOutStringSlice(alldbs, computil.GetGcsSystemDatabasesIgnoreTest(version)) {
		finaldbs = append(finaldbs, db)
	}
	c.dumpDbs = finaldbs
	c.charset, err = c.spiderconn.ShowServerCharset()
	if err != nil {
		logger.Error("get spider charset failed %s", c.charset)
		return err
	}
	c.tmpDumpDir = path.Join(cst.BK_PKG_INSTALL_PATH, "schema_migrate_"+time.Now().Format(cst.TimeLayoutDir))
	if !cmutil.FileExists(c.tmpDumpDir) {
		stderr, err := osutil.StandardShellCommand(false, fmt.Sprintf("mkdir %s && chown -R mysql %s", c.tmpDumpDir,
			c.tmpDumpDir))
		if err != nil {
			logger.Error("init dir %s failed %s,stderr:%s ", c.tmpDumpDir, err.Error(), stderr)
			return err
		}
	}
	c.tmpDumpFile = time.Now().Format(cst.TimeLayoutDir) + "_schema.sql"
	c.maxThreads = runtime.NumCPU() / 3
	if c.maxThreads < 1 {
		c.maxThreads = 1
	}
	return err
}

// Migrate TODO
func (c *ImportSchemaFromLocalSpiderComp) Migrate() (err error) {
	_, err = c.tdbctlConn.Exec("set global tc_ignore_partitioning_for_create_table = 1;")
	if err != nil {
		logger.Error("set global tc_ignore_partitioning_for_create_table failed %s", err.Error())
		return err
	}
	defer func() {
		_, errx := c.tdbctlConn.Exec("set global tc_ignore_partitioning_for_create_table = 0;")
		if errx != nil {
			logger.Warn("set close tc_ignore_partitioning_for_create_table failed %s", errx.Error())
		}
	}()
	if !c.Params.Stream {
		return c.commonMigrate()
	}
	return c.streamMigrate()
}

func (c *ImportSchemaFromLocalSpiderComp) streamMigrate() (err error) {
	logger.Info("will create mydumper.cnf ...")
	mydumperCnf := path.Join(c.tmpDumpDir, "mydumper.cnf")
	if !cmutil.FileExists(mydumperCnf) {
		if err = os.WriteFile(mydumperCnf, []byte("[myloader_session_variables]\ntc_admin=0\n"), 0666); err != nil {
			logger.Error("create mydumper.cnf failed %s", err.Error())
			return err
		}
	}
	logger.Info("create mydumper.cnf success~ ")
	streamFlow := mysqlutil.MyStreamDumpLoad{
		Dumper: &mysqlutil.MyDumper{
			Host:    c.Params.Host,
			Port:    c.Params.SpiderPort,
			User:    c.adminUser,
			Pwd:     c.adminPwd,
			Charset: c.charset,
			Options: mysqlutil.MyDumperOptions{
				Threads:   2,
				NoData:    true,
				UseStream: true,
				Regex:     "^(?!(mysql|infodba_schema|information_schema|performance_schema|sys))",
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
				Threads:        2,
				UseStream:      true,
				DefaultsFile:   mydumperCnf,
				OverWriteTable: c.Params.DropBefore,
			},
		},
	}
	return streamFlow.Run()
}

// commonMigrate 使用mysqldump 原生方式去迁移
func (c *ImportSchemaFromLocalSpiderComp) commonMigrate() (err error) {
	if len(c.dumpDbs) == 0 {
		logger.Info("当前没有需要拷贝的表，请检查，直接返回")
		return nil
	}
	if err = c.dumpSchema(); err != nil {
		logger.Error("dump schema failed %s", err.Error())
		return err
	}
	if err = c.loadSchema(); err != nil {
		logger.Error("load schema failed %s", err.Error())
		return err
	}
	return nil
}

// dumpSchema 运行备份表结构
//
//	@receiver c
//	@return err
func (c *ImportSchemaFromLocalSpiderComp) dumpSchema() (err error) {
	var dumper mysqlutil.Dumper
	dumpOption := mysqlutil.MySQLDumpOption{
		NoData:       true,
		AddDropTable: c.Params.DropBefore,
		NeedUseDb:    true,
		DumpRoutine:  true,
		DumpTrigger:  true,
		DumpEvent:    true,
	}

	dumper = &mysqlutil.MySQLDumperTogether{
		MySQLDumper: mysqlutil.MySQLDumper{
			DumpDir:         c.tmpDumpDir,
			Ip:              c.Params.Host,
			Port:            c.Params.SpiderPort,
			DbBackupUser:    c.GeneralParam.RuntimeAccountParam.AdminUser,
			DbBackupPwd:     c.GeneralParam.RuntimeAccountParam.AdminPwd,
			DbNames:         c.dumpDbs,
			DumpCmdFile:     path.Join(cst.MysqldInstallPath, "bin", "mysqldump"),
			Charset:         c.charset,
			MySQLDumpOption: dumpOption,
		},
		OutputfileName: c.tmpDumpFile,
	}
	if err := dumper.Dump(); err != nil {
		logger.Error("dump failed: %s", err.Error())
		return err
	}
	return nil
}

func (c *ImportSchemaFromLocalSpiderComp) loadSchema() (err error) {
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
	}.ExcuteSqlByMySQLClientOne(c.tmpDumpFile, "")
	if err != nil {
		logger.Error("执行导入schema文件:%s 失败:%s", c.tmpDumpFile, err.Error())
		return err
	}
	return nil
}
