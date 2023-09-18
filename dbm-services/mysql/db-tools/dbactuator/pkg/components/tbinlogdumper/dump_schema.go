/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package tbinlogdumper

import (
	"fmt"
	"path"
	"regexp"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// DumpSchemaComp TODO
type DumpSchemaComp struct {
	GeneralParam         *components.GeneralParam `json:"general"`
	Params               DumpSchemaParam          `json:"extend"`
	DumpSchemaRunTimeCtx `json:"-"`
}

// DumpSchemaParam TODO
type DumpSchemaParam struct {
	Host              string `json:"host"  validate:"required,ip"`                              // 当前实例的主机地址
	Port              int    `json:"port"  validate:"required,lt=65536,gte=3306"`               // 当前实例的端口
	TBinlogdumperPort int    `json:"tbinlogdumper_port"  validate:"required,lt=65536,gte=3306"` // 当前TBinlogdumperPort实例的端口
	CharSet           string `json:"charset" validate:"required,checkCharset"`                  // 字符集参数

}

// DumpSchemaRunTimeCtx TODO
type DumpSchemaRunTimeCtx struct {
	dbs            []string // 需要备份的表结构的数据库名称集合
	charset        string   // 当前实例的字符集
	dumpCmd        string
	BackupFileName string // 备份文件
	BackupDir      string
}

// Example godoc
func (c *DumpSchemaComp) Example() interface{} {
	comp := DumpSchemaComp{
		Params: DumpSchemaParam{
			Host:              "1.1.1.1",
			Port:              3306,
			TBinlogdumperPort: 27000,
			CharSet:           "default",
		},
	}
	return comp
}

// Init init
//
//	@receiver c
//	@return err
func (c *DumpSchemaComp) Init() (err error) {
	conn, err := native.InsObject{
		Host: c.Params.Host,
		Port: c.Params.Port,
		User: c.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  c.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.Conn()
	if err != nil {
		logger.Error("Connect %d failed:%s", c.Params.Port, err.Error())
		return err
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
	if len(finaldbs) == 0 {
		return fmt.Errorf("变更实例排除系统库后，再也没有可以变更的库")
	}
	c.dbs = finaldbs
	c.charset = c.Params.CharSet
	if c.Params.CharSet == "default" {
		if c.charset, err = conn.ShowServerCharset(); err != nil {
			logger.Error("获取实例的字符集失败：%s", err.Error())
			return err
		}
	}
	c.BackupDir = cst.DumperDefaultBakDir
	c.BackupFileName = fmt.Sprintf("tbinlogdump_%d_schema_%s.sql", c.Params.TBinlogdumperPort, subcmd.GBaseOptions.NodeId)
	return err
}

// Precheck 预检查
//
//	@receiver c
//	@return err
func (c *DumpSchemaComp) Precheck() (err error) {
	c.dumpCmd = path.Join(cst.MysqldInstallPath, "bin", "mysqldump")
	// to export the table structure from the central control
	// you need to use the mysqldump that comes with the central control

	if !osutil.FileExist(c.dumpCmd) {
		return fmt.Errorf("dumpCmd: %s文件不存在", c.dumpCmd)
	}
	if !osutil.FileExist(c.BackupDir) {
		return fmt.Errorf("backupdir: %s不存在", c.BackupDir)
	}
	return
}

// DumpSchema 运行备份表结构
//
//	@receiver c
//	@return err
func (c *DumpSchemaComp) DumpSchema() (err error) {
	dumper := &mysqlutil.MySQLDumperTogether{
		MySQLDumper: mysqlutil.MySQLDumper{
			DumpDir:      c.BackupDir,
			Ip:           c.Params.Host,
			Port:         c.Params.Port,
			DbBackupUser: c.GeneralParam.RuntimeAccountParam.AdminUser,
			DbBackupPwd:  c.GeneralParam.RuntimeAccountParam.AdminPwd,
			DbNames:      c.dbs,
			DumpCmdFile:  c.dumpCmd,
			Charset:      c.charset,
			MySQLDumpOption: mysqlutil.MySQLDumpOption{
				NoData:       true,
				AddDropTable: true,
				NeedUseDb:    true,
				DumpRoutine:  true,
				DumpTrigger:  false,
			},
		},
		OutputfileName: c.BackupFileName,
	}
	if err := dumper.Dump(); err != nil {
		logger.Error("dump failed: ", err.Error())
		return err
	}
	return nil
}

// ModifyEngine 修改备份文件中引擎
func (c *DumpSchemaComp) ModifyEngine() (err error) {
	EngineName := "REDIS"
	ModifyCmd := fmt.Sprintf(
		"sed -i 's/ENGINE=[^ ]*/ENGINE=%s/g' %s", EngineName, path.Join(c.BackupDir, c.BackupFileName),
	)
	logger.Info("ModifyCmd cmd:%s", ModifyCmd)
	output, err := osutil.ExecShellCommand(false, ModifyCmd)
	if err != nil {
		return fmt.Errorf("execte get an error:%s,%w", output, err)
	}
	return nil
}

// LoadSchema 导入表结构
func (c *DumpSchemaComp) LoadSchema() (err error) {
	err = mysqlutil.ExecuteSqlAtLocal{
		IsForce:          false,
		Charset:          c.charset,
		NeedShowWarnings: false,
		Host:             c.Params.Host,
		Port:             c.Params.TBinlogdumperPort,
		WorkDir:          c.BackupDir,
		User:             c.GeneralParam.RuntimeAccountParam.AdminUser,
		Password:         c.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.ExcuteSqlByMySQLClientOne(c.BackupFileName, "test")
	if err != nil {
		logger.Error("执行%s文件失败", path.Join(c.BackupDir, c.BackupFileName))
		return err
	}
	return nil
}
