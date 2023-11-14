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
	"path"
	"regexp"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
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
	conn, err := native.InsObject{
		Host: c.Params.Host,
		Port: c.Params.SpiderPort,
		User: c.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  c.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.Conn()
	if err != nil {
		logger.Error("Connect spider %d failed:%s", c.Params.Port, err.Error())
		return err
	}
	c.tdbctlConn, err = native.InsObject{
		Host: c.Params.Host,
		Port: c.Params.SpiderPort,
		User: c.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  c.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.Conn()
	if err != nil {
		logger.Error("Connect tdbctl %d failed:%s", c.Params.Port, err.Error())
		return err
	}
	c.tdbctlSocket, err = c.tdbctlConn.ShowSocket()
	if err != nil {
		logger.Warn("get tdbctl socket failed %s", err.Error())
		err = nil
	}
	alldbs, err := conn.ShowDatabases()
	if err != nil {
		logger.Error("show all databases failed:%s", err.Error())
		return err
	}
	version, err := conn.SelectVersion()
	if err != nil {
		logger.Error("获取version failed %s", err.Error())
		return err
	}
	finaldbs := []string{}
	reg := regexp.MustCompile(`^bak_cbs`)
	for _, db := range util.FilterOutStringSlice(alldbs, computil.GetGcsSystemDatabasesIgnoreTest(version)) {
		if reg.MatchString(db) {
			continue
		}
		finaldbs = append(finaldbs, db)
	}
	c.spiderconn = conn
	c.dumpDbs = finaldbs
	c.tmpDumpDir = path.Join(cst.BK_PKG_INSTALL_PATH, "schema_migrate")
	c.tmpDumpFile = time.Now().Format(cst.TimeLayoutDir) + "_schema.sql"
	return err
}

// Migrate TODO
func (c *ImportSchemaFromLocalSpiderComp) Migrate() (err error) {
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
		AddDropTable: true,
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
	}.ExcuteSqlByMySQLClientOne(c.tmpDumpFile, "")
	if err != nil {
		logger.Error("执行导入schema文件:%s 失败:%s", c.tmpDumpFile, err.Error())
		return err
	}
	return nil
}
