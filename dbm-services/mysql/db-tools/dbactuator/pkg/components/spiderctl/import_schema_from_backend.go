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
	"context"
	"database/sql"
	"errors"
	"fmt"
	"log"
	"os"
	"path"
	"regexp"
	"runtime"
	"strings"
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

// Remote shard0 physical DB names are "{logical}_0"; Spider/tdbctl use logical names without _N suffix.
var shard0PhysicalDBName = regexp.MustCompile(`^(.+)_0$`)

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
	// IsSpiderLayerDisasterRecover 为 true 时，只在中控以 tc_admin=1 导入。dump 先改成 CREATE TABLE IF NOT EXISTS，并拒绝 DROP/TRUNCATE。
	IsSpiderLayerDisasterRecover bool `json:"is_spider_layer_disaster_recover"`
}

type importSchemaFromBackendRuntime struct {
	spiderconn        *native.DbWorker
	tdbctlConn        *native.DbWorker
	charset           string
	dumpDbs           []string
	tmpDumpDir        string
	tmpDumpFile       string
	tdbctlSocket      string
	adminUser         string
	adminPwd          string
	maxThreads        int
	spiderAdminUser   string
	spiderAdminPwd    string
	mysqlDumpFileInfo map[string]string
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

// discoverLogicalDbsFromBackend 当 Spider 上尚无业务库（SHOW DATABASES 为逻辑名、无 _0/_1）时，
// 连 Remote 分片 0 实例：仅识别物理库名严格匹配 "{logical}_0"，得到与 Spider 侧一致的逻辑库名列表。
func (c *ImportSchemaFromBackendComp) discoverLogicalDbsFromBackend() ([]string, error) {
	bw, err := native.InsObject{
		Host: c.Params.BackendHost,
		Port: c.Params.BackendPort,
		User: c.Params.TdbctlUser,
		Pwd:  c.Params.TdbctlPass,
	}.Conn()
	if err != nil {
		return nil, fmt.Errorf("connect backend shard0: %w", err)
	}
	defer bw.Close()
	raw, err := bw.ShowDatabases()
	if err != nil {
		return nil, fmt.Errorf("backend show databases: %w", err)
	}
	ver, err := bw.SelectVersion()
	if err != nil {
		return nil, fmt.Errorf("backend select version: %w", err)
	}
	sys := computil.GetGcsSystemDatabases(ver)
	sysSet := make(map[string]struct{}, len(sys))
	for _, s := range sys {
		sysSet[s] = struct{}{}
	}
	seen := make(map[string]struct{})
	var logical []string
	for _, name := range raw {
		if _, ok := sysSet[name]; ok {
			continue
		}
		m := shard0PhysicalDBName.FindStringSubmatch(name)
		if len(m) != 2 {
			continue
		}
		logicName := m[1]
		if logicName == "" {
			continue
		}
		if _, ok := seen[logicName]; ok {
			continue
		}
		seen[logicName] = struct{}{}
		logical = append(logical, logicName)
	}
	return logical, nil
}

// chooseDumpDbs 决定本次要导入的逻辑库。
// 灾难重建以分片 0 的完整名单为准。本机 Spider 上已有的库只代表上次做到哪，不能缩短名单。
// 分片 0 连不上或解析不出业务库时直接失败。追加部署仍优先用 Spider 上已有的库。
func chooseDumpDbs(disaster bool, spiderUserDbs, backendLogicalDbs []string, backendErr error) ([]string, error) {
	if disaster {
		if backendErr != nil {
			return nil, backendErr
		}
		if len(backendLogicalDbs) == 0 {
			return nil, fmt.Errorf("spider layer disaster recover: no {logical}_0 physical DB on backend shard0")
		}
		return backendLogicalDbs, nil
	}
	if len(spiderUserDbs) > 0 {
		return spiderUserDbs, nil
	}
	if backendErr != nil {
		return nil, backendErr
	}
	if len(backendLogicalDbs) == 0 {
		return nil, fmt.Errorf("no user databases on spider and no {logical}_0 physical DB on backend shard0")
	}
	return backendLogicalDbs, nil
}

func quoteMySQLIdent(name string) string {
	return "`" + strings.ReplaceAll(name, "`", "``") + "`"
}

func createDatabaseSQL(disaster bool, db, charset string) string {
	name := quoteMySQLIdent(db)
	if disaster {
		return fmt.Sprintf("CREATE DATABASE IF NOT EXISTS %s /*!40100 DEFAULT CHARACTER SET %s */;", name, charset)
	}
	return fmt.Sprintf("CREATE DATABASE %s /*!40100 DEFAULT CHARACTER SET %s */;", name, charset)
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
	spiderUserDbs := util.FilterOutStringSlice(alldbs, computil.GetGcsSystemDatabases(version))
	var backendLogicalDbs []string
	var backendErr error
	if c.Params.IsSpiderLayerDisasterRecover || len(spiderUserDbs) == 0 {
		backendLogicalDbs, backendErr = c.discoverLogicalDbsFromBackend()
	}
	finaldbs, chooseErr := chooseDumpDbs(c.Params.IsSpiderLayerDisasterRecover, spiderUserDbs, backendLogicalDbs, backendErr)
	if chooseErr != nil {
		return chooseErr
	}
	if c.Params.IsSpiderLayerDisasterRecover {
		logger.Info("import-schema-to-tdbctl: disaster recover uses backend shard0 list: %v", finaldbs)
	} else if len(spiderUserDbs) == 0 {
		logger.Info("import-schema-to-tdbctl: spider has no user databases, using backend shard0 list: %v", finaldbs)
	}
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
		// nolint
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
		// nolint
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

// DisableTcAdmin set tc_admin=0
func (c *ImportSchemaFromBackendComp) DisableTcAdmin() (err error) {
	return c.setTcAdmin(0)
}

// EnableTcAdmin set tc_admin=1
func (c *ImportSchemaFromBackendComp) EnableTcAdmin() (err error) {
	return c.setTcAdmin(1)
}

// setTcAdmin set tc_admin flag
func (c *ImportSchemaFromBackendComp) setTcAdmin(flag int) (err error) {
	_, err = c.tdbctlConn.Exec("set global tc_admin=?;", flag)
	if err != nil {
		return err
	}
	return nil
}

// dumpMysqlSchemaFilesToWorkdir mysqldump 仅落盘到 tmpDumpDir，并填充 mysqlDumpFileInfo（spider-only 从节点复用）
var destructiveSchemaSQL = regexp.MustCompile(`(?i)\b(DROP\s+TABLE|DROP\s+DATABASE|TRUNCATE(?:\s+TABLE)?)\b`)

func rejectDestructiveSchemaSQL(raw string) error {
	found := destructiveSchemaSQL.FindString(raw)
	if found == "" {
		return nil
	}
	return fmt.Errorf("refuse schema import: destructive statement %q", found)
}

func rewriteCreateTableIfNotExists(raw string) string {
	lines := strings.Split(raw, "\n")
	for i, line := range lines {
		if strings.HasPrefix(line, "CREATE TABLE IF NOT EXISTS ") {
			continue
		}
		if strings.HasPrefix(line, "CREATE TABLE `") {
			lines[i] = "CREATE TABLE IF NOT EXISTS " + strings.TrimPrefix(line, "CREATE TABLE ")
		}
	}
	return strings.Join(lines, "\n")
}

func prepareCtlForwardSchemaFile(filePath string) error {
	rawBytes, err := os.ReadFile(filePath)
	if err != nil {
		return err
	}
	raw := string(rawBytes)
	if err = rejectDestructiveSchemaSQL(raw); err != nil {
		return err
	}
	rewritten := rewriteCreateTableIfNotExists(raw)
	if rewritten == raw {
		return nil
	}
	tmp := filePath + ".rewrite"
	if err = os.WriteFile(tmp, []byte(rewritten), 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, filePath)
}

func (c *ImportSchemaFromBackendComp) prepareCtlForwardSchemaFiles() error {
	for _, name := range c.mysqlDumpFileInfo {
		if err := prepareCtlForwardSchemaFile(path.Join(c.tmpDumpDir, name)); err != nil {
			return err
		}
	}
	return nil
}

func (c *ImportSchemaFromBackendComp) dumpMysqlSchemaFilesToWorkdir() (err error) {
	if len(c.dumpDbs) == 0 {
		return nil
	}
	if c.Params.IsSpiderLayerDisasterRecover {
		c.Params.DropBefore = false
	}
	dumpOption := mysqlutil.MySQLDumpOption{
		DumpSchema:              true,
		NoCreateDb:              true,
		NoUseDbAndWirteCreateDb: true,
		AddDropTable:            c.Params.DropBefore,
		DumpRoutine:             false,
		DumpTrigger:             false,
		DumpEvent:               false,
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
	c.mysqlDumpFileInfo = dumper.GetDumpFileInfo()
	return nil
}

// migrateUseMysqlDump 运行备份表结构
// nolint
func (c *ImportSchemaFromBackendComp) migrateUseMysqlDump() (err error) {
	if len(c.dumpDbs) == 0 {
		logger.Info("当前没有需要拷贝的表，请检查，直接返回")
		return nil
	}
	if err = c.dumpMysqlSchemaFilesToWorkdir(); err != nil {
		return err
	}
	if c.Params.IsSpiderLayerDisasterRecover {
		if err = c.prepareCtlForwardSchemaFiles(); err != nil {
			return err
		}
	}
	logger.Info("备份表结构成功,开始导入表结构到中控")
	dumpfileInfo := c.mysqlDumpFileInfo
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
	if c.Params.IsSpiderLayerDisasterRecover {
		loader.InitCommand = "SET SESSION tc_admin=1"
	}
	errChan := make(chan error)
	wg := sync.WaitGroup{}
	ctrChan := make(chan struct{}, c.maxThreads)
	for _, db := range c.dumpDbs {
		conn, err := c.tdbctlConn.Db.Conn(context.Background())
		if err != nil {
			logger.Error("从连接池获取连接失败:%s", err.Error())
			return err
		}
		wg.Add(1)
		dumpfile := dumpfileInfo[buildBackendDb(db)]
		go func(conn *sql.Conn, db string, dumpfile string) {
			ctrChan <- struct{}{}
			defer func() { wg.Done(); <-ctrChan }()
			defer conn.Close()
			tcAdminSQL := "set tc_admin=0;"
			if c.Params.IsSpiderLayerDisasterRecover {
				tcAdminSQL = "set tc_admin=1;"
			}
			createDBSQL := createDatabaseSQL(c.Params.IsSpiderLayerDisasterRecover, db, c.charset)
			if _, execErr := conn.ExecContext(context.Background(), tcAdminSQL); execErr != nil {
				logger.Error("set session tc_admin failed:%s", execErr.Error())
				errChan <- execErr
				return
			}
			if _, execErr := conn.ExecContext(context.Background(), createDBSQL); execErr != nil {
				logger.Error("创建数据库:%s 失败:%s", db, execErr.Error())
				errChan <- execErr
				return
			}
			if execErr := loader.ExecuteSqlByMySQLClientOne(dumpfile, db, true); execErr != nil {
				logger.Error("执行导入schema文件:%s 失败:%s", dumpfile, execErr.Error())
				errChan <- execErr
			}
		}(conn, db, dumpfile)
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

// MigrateRoutinesAndTrigger 从spider导出存储过程、触发器、event导入到中控
func (c *ImportSchemaFromBackendComp) MigrateRoutinesAndTrigger() (err error) {
	logger.Info("will import routines and triggers to tdbctl")
	conn, err := c.tdbctlConn.Db.Conn(context.Background())
	if err != nil {
		logger.Error("从连接池获取连接失败:%s", err.Error())
		return err
	}
	_, err = conn.ExecContext(context.Background(), "set tc_admin=0;")
	if err != nil {
		logger.Error("set session tc_admin=0 failed:%s", err.Error())
		return err
	}
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

// MigrateViewsFromSpider 从spider导出视图导入到中控
func (c *ImportSchemaFromBackendComp) MigrateViewsFromSpider() (err error) {
	// get all views from spiderconn
	var views []native.View
	if views, err = c.spiderconn.GetAllViews(); err != nil {
		logger.Error("show views from spider conn failed: %s", err.Error())
		return err
	}
	logger.Info("get all views from spider conn success, views:%d", len(views))
	for _, view := range views {
		logger.Info("import view: %s.%s", view.DbName, view.Name)
		var viewName, viewSQL, charsetClient, collationClient string
		err = c.spiderconn.Db.QueryRow(fmt.Sprintf("show create view `%s`.`%s`", view.DbName, view.Name)).Scan(&viewName,
			&viewSQL,
			&charsetClient,
			&collationClient)
		if err != nil {
			log.Fatal("Error fetching view:", err)
		}
		if _, err = c.tdbctlConn.Exec(viewSQL); err != nil {
			logger.Error("import view failed: %s", err.Error())
			return err
		}
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
