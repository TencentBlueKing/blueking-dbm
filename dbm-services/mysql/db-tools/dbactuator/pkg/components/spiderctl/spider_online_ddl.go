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
	"fmt"
	"math/rand/v2"
	"os"
	"path"
	"strings"

	"github.com/samber/lo"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/ghost"
)

// SpiderOnlineDDLComp use gh-ost do online ddl
type SpiderOnlineDDLComp struct {
	mysql.ExecuteSQLFileComp
	TendbClusterOnlineDDLCtx
}

// TendbClusterOnlineDDLCtx online ddl ctx
type TendbClusterOnlineDDLCtx struct {
	masterSptSvrs map[int][]native.Server
	// spiderSvrMap  map[int][]native.Server
	spiderConnMap map[int][]MasterSpiderConn
	taskdir       string
	dbConns       map[int]*native.TdbctlDbWork
	ports         []int
	ghostcmdFd    *os.File
	billId        uint
}

// MasterSpiderConn master spider conn
type MasterSpiderConn struct {
	Name      string
	Host      string
	Port      int
	ConnPool  *sql.DB
	IsSpider3 bool
}

// Init prepare run env
func (c *SpiderOnlineDDLComp) Init() (err error) {
	c.masterSptSvrs = make(map[int][]native.Server)
	// c.spiderSvrMap = make(map[int][]native.Server)
	c.spiderConnMap = make(map[int][]MasterSpiderConn)
	c.ports = make([]int, len(c.Params.Ports))
	copy(c.ports, c.Params.Ports)
	c.dbConns = make(map[int]*native.TdbctlDbWork)
	for _, port := range c.ports {
		var dbConn *native.DbWorker
		var svrs []native.Server
		dbConn, err = native.InsObject{
			Host: c.Params.Host,
			Port: port,
			User: c.GeneralParam.RuntimeAccountParam.AdminUser,
			Pwd:  c.GeneralParam.RuntimeAccountParam.AdminPwd,
		}.Conn()
		if err != nil {
			logger.Error("Connect %d failed:%s", port, err.Error())
			return err
		}
		tdbctlConn := &native.TdbctlDbWork{DbWorker: *dbConn}
		svrs, err = tdbctlConn.SelectServers()
		if err != nil {
			logger.Error("SelectServers failed:%s", err.Error())
			return err
		}
		for _, svr := range svrs {
			if native.SvrNameIsMasterShard(svr.ServerName) {
				c.masterSptSvrs[port] = append(c.masterSptSvrs[port], svr)
			}
			if native.SvrNameIsMasterSpiderShard(svr.ServerName) || native.SvrNameIsSlaveSpiderShard(svr.ServerName) {
				conn, errx := svr.Opendb("")
				if errx != nil {
					logger.Error("Connect spider %s failed:%s", svr.ServerName, errx.Error())
					return errx
				}
				var spider_version string
				err = conn.QueryRow("select version()").Scan(&spider_version)
				if err != nil {
					logger.Error("Connect spider %s failed:%s", svr.ServerName, err.Error())
					return err
				}
				isSpider3 := false
				if strings.Contains(spider_version, "-tspider-3.") {
					isSpider3 = true
				}
				c.spiderConnMap[port] = append(c.spiderConnMap[port], MasterSpiderConn{
					Name:      svr.ServerName,
					Host:      svr.Host,
					Port:      svr.Port,
					ConnPool:  conn,
					IsSpider3: isSpider3,
				})
			}
		}
		c.dbConns[port] = tdbctlConn
	}
	c.taskdir = strings.TrimSpace(c.Params.FilePath)
	if c.taskdir == "" {
		c.taskdir = cst.BK_PKG_INSTALL_PATH
	}
	ghostcmdFile := path.Join(c.taskdir, "gh_ost_cmd.txt")
	logger.Info("如果在执行过程中部分节点失败，可以在%s中查看执行命令", ghostcmdFile)
	c.ghostcmdFd, err = os.OpenFile(ghostcmdFile, os.O_RDWR|os.O_CREATE, 0600)
	if err != nil {
		logger.Error("create文件%s 失败:%s", ghostcmdFile, err.Error())
		return err
	}
	if c.Params.BillId != 0 {
		c.billId = c.Params.BillId
	} else {
		c.billId = rand.Uint()
	}
	return err
}

// Execute executes the component.
//
// The component executes online DDL operations on spider clusters.
//
// The ports parameter is a list of integers representing the ports of the
// spider clusters to execute on.
//
// The function returns an error if it fails to execute on any of the ports.
func (c *SpiderOnlineDDLComp) Execute() error {
	for _, port := range c.ports {
		if err := c.executeOne(port); err != nil {
			logger.Error("execute at %d failed: %s", port, err.Error())
			return err
		}
	}
	return nil
}

// Close close open fd
func (c *SpiderOnlineDDLComp) Close() error {
	c.ghostcmdFd.Close()
	for _, dbConn := range c.dbConns {
		if dbConn != nil {
			dbConn.Close()
		}
	}
	return nil
}

// Precheck precheck
func (c *SpiderOnlineDDLComp) Precheck() (err error) {
	// 提前解析下文件
	for _, f := range c.Params.ExecuteObjects {
		for _, sqlFile := range f.SQLFiles {
			var fileContent []byte
			fileContent, err = os.ReadFile(path.Join(c.taskdir, sqlFile))
			if err != nil {
				logger.Error("读取文件%s失败:%s", path.Join(c.taskdir, sqlFile), err.Error())
				return err
			}
			var sqlLines []string
			sqlLines, err = ghost.ParseSQLFile(string(fileContent))
			if err != nil {
				logger.Error("解析sql文件%s失败:%s", sqlFile, err.Error())
				return err
			}
			if err = c.writeSplitSQLToFile(sqlFile, sqlLines); err != nil {
				logger.Error("将解析后的SQL写入文件%s失败:%s", sqlFile, err.Error())
				return err
			}
		}
	}
	return err
}

// executeOne execute
func (c *SpiderOnlineDDLComp) executeOne(port int) (err error) {
	alldbs, err := c.dbConns[port].ShowDatabases()
	if err != nil {
		logger.Error("获取实例db list失败:%s", err.Error())
		return err
	}
	dbsExcluesysdbs := util.FilterOutStringSlice(alldbs, computil.GetGcsSystemDatabasesIgnoreTest("5.7"))
	for _, f := range c.Params.ExecuteObjects {
		var realexcutedbs, intentionDbs, ignoreDbs []string
		// 获得目标库 因为是通配符 所以需要获取完整名称
		intentionDbs, err = c.Match(dbsExcluesysdbs, f.ParseDbParamRe())
		if err != nil {
			return err
		}
		// 获得忽略库
		ignoreDbs, err = c.Match(dbsExcluesysdbs, f.ParseIgnoreDbParamRe())
		if err != nil {
			return err
		}
		// 获取最终需要执行的库
		realexcutedbs = util.FilterOutStringSlice(intentionDbs, ignoreDbs)
		if len(realexcutedbs) == 0 {
			return fmt.Errorf("没有适配到任何需要变更的db,可能db不存在请检查")
		}
		logger.Info("will real excute on %v", realexcutedbs)
		for _, dbName := range realexcutedbs {
			for _, sqlFile := range f.SQLFiles {
				var fileContent []byte
				fileContent, err = os.ReadFile(path.Join(c.taskdir, sqlFile))
				if err != nil {
					logger.Error("读取文件%s失败:%s", path.Join(c.taskdir, sqlFile), err.Error())
					return err
				}
				var sqlLines []string
				sqlLines, err = ghost.ParseSQLFile(string(fileContent))
				if err != nil {
					logger.Error("解析sql文件%s失败:%s", sqlFile, err.Error())
					return err
				}
				var realdb string
				realdb = dbName
				for _, sqlLine := range sqlLines {
					logger.Info("will execute sql: %s", sqlLine)
					var db, tb string
					isUseDb, thedb := ghost.IsUseDb(sqlLine)
					if isUseDb {
						realdb = thedb
						continue
					}
					isAlter, doSpiderFirst := ghost.IsAlterSQL(sqlLine)
					if isAlter {
						db, tb, err = ghost.ParseSqlSchemaInfo(sqlLine)
						if err != nil {
							return err
						}
						if lo.IsNotEmpty(db) {
							realdb = db
						}
						// is alter table using online ddl
						err = c.ExecuteByPassTdbctl(port, realdb, tb, sqlLine, doSpiderFirst)
						if err != nil {
							return err
						}
					} else {
						// common sql execute in tdbctl
						_, err = c.dbConns[port].ExecMore([]string{fmt.Sprintf("use `%s`;", realdb), sqlLine})
						if err != nil {
							logger.Error("执行sql:%s 失败:%s", sqlLine, err.Error())
							return err
						}
					}
				}
			}
		}
	}
	return err
}
func (c *SpiderOnlineDDLComp) buildUserGhostFlag() ghost.UserGhostFlag {
	allowOnMaster := true
	maxload := "Threads_running=30,Threads_connected=2000"
	engine := c.Params.Engine
	if lo.IsEmpty(c.Params.Engine) {
		engine = "innodb"
	}
	return ghost.UserGhostFlag{AllowOnMaster: &allowOnMaster, MaxLoad: &maxload, StorageEngine: &engine}
}

// ExecuteByPassTdbctl run online ddl by bypass tdbctl
func (c *SpiderOnlineDDLComp) ExecuteByPassTdbctl(port int, db, tb, statement string, doSpiderFirst bool) (err error) {
	var runSteps []func() error
	ghostFlag := c.buildUserGhostFlag()
	c.writeghotcmd(port, db, tb, statement, ghostFlag)
	if doSpiderFirst {
		logger.Info("[step1] 执行sql:%s on spider", statement)
		runSteps = append(runSteps, func() error {
			return c.applySchemaChangeOnSpiders(port, db, statement)
		})
		logger.Info("[step2] 执行sql:%s on backend", statement)
		runSteps = append(runSteps, func() error {
			return ghost.RunMigratorClustershardNodes(c.masterSptSvrs[port], c.billId, db, tb, statement, ghostFlag)
		})
	} else {
		logger.Info("[step1] 执行sql:%s on backend", statement)
		runSteps = append(runSteps, func() error {
			return ghost.RunMigratorClustershardNodes(c.masterSptSvrs[port], c.billId, db, tb, statement, ghostFlag)
		})
		logger.Info("[step2] 执行sql:%s on spider", statement)
		runSteps = append(runSteps, func() error {
			return c.applySchemaChangeOnSpiders(port, db, statement)
		})
	}
	for _, step := range runSteps {
		if err = step(); err != nil {
			return err
		}
	}
	logger.Info("[step3] 执行sql:%s on tdbctl", statement)
	// 最后在中控上执行对应的sql
	_, err = c.dbConns[port].ExecMore([]string{"set tc_admin=0", fmt.Sprintf("use `%s`;", db), statement})
	return err
}

func (c *SpiderOnlineDDLComp) writeghotcmd(port int, db, tb, statement string, ghostFlag ghost.UserGhostFlag) {
	cmdlines := ghost.BuildGhostCmdEveryNodes(c.masterSptSvrs[port], c.billId, db, tb, statement, ghostFlag)
	for _, cmdline := range cmdlines {
		// nolint
		c.ghostcmdFd.WriteString(cmdline + "\n")
	}
}

func (c *SpiderOnlineDDLComp) writeSplitSQLToFile(originFile string, statements []string) (err error) {
	fileName := path.Join(c.taskdir, fmt.Sprintf("%s_split.sql", originFile))
	if cmutil.FileExists(fileName) {
		return nil
	}
	fd, err := os.OpenFile(fileName, os.O_CREATE|os.O_RDWR|os.O_APPEND, 0644)
	if err != nil {
		return err
	}
	defer fd.Close()
	for _, statement := range statements {
		_, err = fd.WriteString(statement + "\n")
		if err != nil {
			return err
		}
	}
	return err
}

// applySchemaChaneOnSpiders apply schema change on spiders
func (c *SpiderOnlineDDLComp) applySchemaChangeOnSpiders(port int, db, statement string) (err error) {
	logger.Info("execute on  %s all spiders 执行sql:%s", db, statement)
	for _, spc := range c.spiderConnMap[port] {
		// 使用每次迭代内的匿名函数，确保连接在本次迭代结束时关闭
		if err = func() error {
			conn, innerErr := spc.ConnPool.Conn(context.Background())
			if innerErr != nil {
				logger.Error("get conn from [%s:%d] 失败:%s", spc.Host, spc.Port, innerErr.Error())
				return innerErr
			}
			defer conn.Close()

			if spc.IsSpider3 {
				_, innerErr = conn.ExecContext(context.Background(), "set ddl_execute_by_ctl = 0;")
				if innerErr != nil {
					logger.Error("set ddl_execute_by_ctl = 0 on [%s:%d] 失败:%s", spc.Host, spc.Port, innerErr.Error())
					return innerErr
				}
			}
			_, innerErr = conn.ExecContext(context.Background(), fmt.Sprintf("use %s;", db))
			if innerErr != nil {
				logger.Error("use %s 失败:%s", db, innerErr.Error())
				return innerErr
			}
			_, innerErr = conn.ExecContext(context.Background(), statement)
			if innerErr != nil {
				logger.Error("execute on:[%s:%d] 执行sql:%s 失败:%s", spc.Host, spc.Port, statement, innerErr.Error())
				return innerErr
			}
			return nil
		}(); err != nil {
			logger.Error("execute on [%s:%d] 执行sql:%s 失败:%s", spc.Host, spc.Port, statement, err.Error())
			return err
		}
	}
	return nil
}
