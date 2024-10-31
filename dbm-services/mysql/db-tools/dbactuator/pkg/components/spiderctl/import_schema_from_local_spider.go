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
	Host        string `json:"host"  validate:"required,ip"`                       // 当前实例的主机地址
	Port        int    `json:"port"  validate:"required,lt=65536,gte=3306"`        // 当前实例的端口
	SpiderPort  int    `json:"spider_port"  validate:"required,lt=65536,gte=3306"` // spider节点端口
	UseMydumper bool   `json:"use_mydumper"`                                       // use mydumper
	Stream      bool   `json:"stream"`                                             // mydumper stream myloader stream
	DropBefore  bool   `json:"drop_before"`                                        // 强制覆盖原来的表结构
	Threads     int    `json:"threads"`                                            // 可配置最大并发 for mydumper myloader
	TdbctlUser  string `json:"tdbctl_user" validate:"required"`
	TdbctlPass  string `json:"tdbctl_pass" validate:"required"`
}

type importSchemaFromLocalSpiderRuntime struct {
	spiderconn      *native.DbWorker
	tdbctlConn      *native.DbWorker
	tdbctlConns     []*native.DbWorker
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
func (c *ImportSchemaFromLocalSpiderComp) Example() interface{} {
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
	if err = c.initSlaveTdbctlConns(); err != nil {
		logger.Error("init slave tdbctl conns failed %s", err.Error())
		return err
	}
	return err
}

// initSlaveTdbctlConns init slave tdbctl conns
func (c *ImportSchemaFromLocalSpiderComp) initSlaveTdbctlConns() (err error) {
	tconn := native.TdbctlDbWork{
		DbWorker: *c.tdbctlConn,
	}
	servers, err := tconn.SelectServers()
	if err != nil {
		logger.Error("select servers failed %s", err.Error())
	}
	var tdbctlServers []native.Server
	for _, server := range servers {
		if native.SvrNameIsTdbctl(server.ServerName) {
			tdbctlServers = append(tdbctlServers, server)
		}
	}
	for _, server := range tdbctlServers {
		conn, err := native.InsObject{
			Host: server.Host,
			Port: server.Port,
			User: server.Username,
			Pwd:  server.Password,
		}.Conn()
		if err != nil {
			return err
		}
		c.tdbctlConns = append(c.tdbctlConns, conn)
	}
	return
}

func (c *ImportSchemaFromLocalSpiderComp) enableTcIgnore() (err error) {
	for _, c := range c.tdbctlConns {
		_, err = c.Exec("set global tc_ignore_partitioning_for_create_table = 1;")
		if err != nil {
			return err
		}
	}
	return
}

func (c *ImportSchemaFromLocalSpiderComp) disableTcIgnore() (err error) {
	for _, c := range c.tdbctlConns {
		_, err = c.Exec("set global tc_ignore_partitioning_for_create_table = 0;")
		if err != nil {
			return err
		}
	}
	return
}

func (c *ImportSchemaFromLocalSpiderComp) closeSlavetdbctlConns() {
	for _, c := range c.tdbctlConns {
		if c != nil {
			c.Close()
		}
	}
}

// Migrate migrate local spider schema to tdbctl
func (c *ImportSchemaFromLocalSpiderComp) Migrate() (err error) {
	if err = c.enableTcIgnore(); err != nil {
		return err
	}
	defer func() {
		// 从库会有延迟的操作,此时不能关闭 tc_ignore_partitioning_for_create_table = 0
		// errx := c.disableTcIgnore()
		// if errx != nil {
		// 	logger.Warn("set close tc_ignore_partitioning_for_create_table failed %s", errx.Error())
		// }
		c.closeSlavetdbctlConns()
	}()
	if c.Params.UseMydumper {
		if c.Params.Stream {
			return c.streamMigrate()
		}
		return c.mydumperCommonMigrate()
	}
	return c.commonMigrate()

}

func (c *ImportSchemaFromLocalSpiderComp) streamMigrate() (err error) {
	logger.Info("will create mydumper.cnf ...")
	mydumperCnf := path.Join(c.tmpDumpDir, "mydumper.cnf")
	if !cmutil.FileExists(mydumperCnf) {
		if err = os.WriteFile(mydumperCnf, []byte("[myloader_session_variables]\n	tc_admin=0\n"), 0666); err != nil {
			logger.Error("create mydumper.cnf failed %s", err.Error())
			return err
		}
	}
	logger.Info("create mydumper.cnf success~ ")
	streamFlow := mysqlutil.MyStreamDumpLoad{
		Dumper: &mysqlutil.MyDumper{
			Host:    c.Params.Host,
			Port:    c.Params.SpiderPort,
			User:    c.spiderAdminUser,
			Pwd:     c.spiderAdminPwd,
			Charset: c.charset,
			Options: mysqlutil.MyDumperOptions{
				Threads:   c.maxThreads,
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
				Threads:        c.maxThreads,
				UseStream:      true,
				DefaultsFile:   mydumperCnf,
				OverWriteTable: c.Params.DropBefore,
			},
		},
	}
	return streamFlow.Run()
}

// mydumperCommonMigrate TODO
func (c *ImportSchemaFromLocalSpiderComp) mydumperCommonMigrate() (err error) {
	logger.Info("will create mydumper.cnf ...")
	mydumperCnf := path.Join(c.tmpDumpDir, "mydumper.cnf")
	if !cmutil.FileExists(mydumperCnf) {
		if err = os.WriteFile(mydumperCnf, []byte("[myloader_session_variables]\n	tc_admin=0\n"), 0666); err != nil {
			logger.Error("create mydumper.cnf failed %s", err.Error())
			return err
		}
	}
	dumper := &mysqlutil.MyDumper{
		Host:    c.Params.Host,
		Port:    c.Params.SpiderPort,
		User:    c.spiderAdminUser,
		Pwd:     c.spiderAdminPwd,
		Charset: c.charset,
		DumpDir: c.tmpDumpDir,
		Options: mysqlutil.MyDumperOptions{
			Threads:   c.maxThreads,
			NoData:    true,
			UseStream: false,
			Regex:     "^(?!(mysql|infodba_schema|information_schema|performance_schema|sys))",
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
	return nil
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
		DumpSchema:   true,
		AddDropTable: c.Params.DropBefore,
		DumpRoutine:  true,
		DumpTrigger:  true,
		DumpEvent:    true,
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
	}.ExecuteSqlByMySQLClientOne(c.tmpDumpFile, "", true)
	if err != nil {
		logger.Error("执行导入schema文件:%s 失败:%s", c.tmpDumpFile, err.Error())
		return err
	}
	return nil
}
