/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package mysql TODO
//
//	ignore_dbnames: 变更时候需要忽略的dbname,支持正则匹配 [db1,db2,db3%]
//	dbnames: 变更时候 需要指定的变更的库
package mysql

import (
	"errors"
	"fmt"
	"path"
	"regexp"
	"strings"

	"github.com/samber/lo"

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

// ExecuteSQLFileComp excute sql file component
type ExecuteSQLFileComp struct {
	GeneralParam             *components.GeneralParam `json:"general"`
	Params                   *ExecuteSQLFileParam     `json:"extend"`
	ExecuteSQLFileRunTimeCtx `json:"-"`
}

// ExecuteSQLFileParam excute sql file param
type ExecuteSQLFileParam struct {
	Host           string              `json:"host"  validate:"required,ip"`             // 当前实例的主机地址
	Ports          []int               `json:"ports"`                                    // 被监控机器的上所有需要监控的端口
	CharSet        string              `json:"charset" validate:"required,checkCharset"` // 字符集参数
	FilePath       string              `json:"file_path"`                                // 文件路径
	FilePathSubfix string              `json:"file_path_suffix"`
	FileBaseDir    string              `json:"file_base_dir"`
	ExecuteObjects []ExecuteSQLFileObj `json:"execute_objects"`
	Force          bool                `json:"force"`     // 是否强制执行 执行出错后，是否继续往下执行
	IsSpider       bool                `json:"is_spider"` // 是否是spider集群
}

// ExecuteSQLFileObj 单个文件的执行对象
// 一次可以多个文件操作不同的数据库
type ExecuteSQLFileObj struct {
	//	SQLFile string `json:"sql_file"` // 变更文件名称
	LineId        int      `json:"line_id"`
	SQLFiles      []string `json:"sql_files"`      // 变更文件名称
	IgnoreDbNames []string `json:"ignore_dbnames"` // 忽略的,需要排除变更的dbName,支持模糊匹配
	DbNames       []string `json:"dbnames"`        // 需要变更的DBNames,支持模糊匹配
}

// ExecuteSQLFileRunTimeCtx 运行时上下文
type ExecuteSQLFileRunTimeCtx struct {
	ports      []int
	dbConns    map[Port]*native.DbWorker
	vermap     map[Port]string // 当前实例的数据版本
	charsetmap map[Port]string // 当前实例的字符集
	socketmap  map[Port]string // 当前实例的socket value
	taskdir    string
}

// Example TODO
func (e *ExecuteSQLFileComp) Example() interface{} {
	return ExecuteSQLFileComp{
		GeneralParam: &components.GeneralParam{},
		Params: &ExecuteSQLFileParam{
			Host:           "127.0.0.1",
			Ports:          []int{3306, 3307},
			CharSet:        "utf8",
			FilePath:       "/data/workspace",
			FileBaseDir:    "/datta",
			FilePathSubfix: "sqlfile_",
			ExecuteObjects: []ExecuteSQLFileObj{
				{
					SQLFiles:      []string{"111.sql"},
					IgnoreDbNames: []string{"a%"},
					DbNames:       []string{"db1", "db2"},
				},
			},
			Force:    false,
			IsSpider: false,
		},
	}
}

// Precheck do some check step
func (e *ExecuteSQLFileComp) Precheck() (err error) {
	if err = e.checkSQLFileExist(); err != nil {
		logger.Error("SQL文件存在性检查失败:%s", err.Error())
		return err
	}
	for _, port := range e.ports {
		if err = e.checkDuplicateObjects(port); err != nil {
			return err
		}
	}
	return
}

func (e *ExecuteSQLFileComp) cleanHistorySQLDir() {
	if e.Params.FilePathSubfix == "" {
		return
	}
	cleanCmd := fmt.Sprintf(`find %s -maxdepth 1 -name %s* -type d -mtime +60 |xargs -i rm {};`, cst.BK_PKG_INSTALL_PATH,
		e.Params.FilePathSubfix)
	logger.Warn("delete before 60 days dump sql file")
	logger.Warn("will execute: %s", cleanCmd)
	out, err := osutil.StandardShellCommand(false, cleanCmd)
	if err != nil {
		logger.Error("clean sql file failed:%s,out:%s", err.Error(), out)
		return
	}
	logger.Warn("clean sql file success")
}

// checkSQLFileExist 检查文件是否存在
func (e *ExecuteSQLFileComp) checkSQLFileExist() (err error) {
	var errs []error
	for _, f := range e.Params.ExecuteObjects {
		for _, sqlFile := range f.SQLFiles {
			if !cmutil.FileExists(path.Join(e.taskdir, sqlFile)) {
				err = fmt.Errorf("文件不存在:%s", sqlFile)
				errs = append(errs, err)
			}
		}
	}
	return errors.Join(errs...)
}

// checkDuplicateObjects  判断每行变更对象，是否存在相同文件变更相同db的情况
func (e *ExecuteSQLFileComp) checkDuplicateObjects(port int) (err error) {
	var errs []error
	alldbs, err := e.dbConns[port].ShowDatabases()
	if err != nil {
		logger.Error("获取实例db list失败:%s", err.Error())
		return err
	}
	dbsExcluesysdbs := util.FilterOutStringSlice(alldbs, computil.GetGcsSystemDatabasesIgnoreTest(e.vermap[port]))
	m := make(map[int][]string)
	for _, f := range e.Params.ExecuteObjects {
		var realexcutedbs []string
		// 获得目标库 因为是通配符 所以需要获取完整名称
		intentionDbs, err := e.match(dbsExcluesysdbs, f.parseDbParamRe())
		if err != nil {
			return err
		}
		// 获得忽略库
		ignoreDbs, err := e.match(dbsExcluesysdbs, f.parseIgnoreDbParamRe())
		if err != nil {
			return err
		}
		// 获取最终需要执行的库
		realexcutedbs = util.FilterOutStringSlice(intentionDbs, ignoreDbs)
		m[f.LineId] = realexcutedbs
	}
	total := len(e.Params.ExecuteObjects)
	for i, baseObj := range e.Params.ExecuteObjects {
		for j := i + 1; j < total; j++ {
			nextObj := e.Params.ExecuteObjects[j]
			duplicateFiles := lo.Intersect(baseObj.SQLFiles, nextObj.SQLFiles)
			// 如果上一行于下一行存在文件交集
			if len(duplicateFiles) > 0 {
				// 	则判断上一行和下一行变更的db对象是否存在重叠
				baseObjdbs := m[baseObj.LineId]
				nextObjdbs := m[nextObj.LineId]
				duplicatedbs := lo.Intersect(baseObjdbs, nextObjdbs)
				if len(duplicatedbs) > 0 {
					errs = append(errs, fmt.Errorf("第%d行和第%d行存在变相同的db:%v,该文件会变更多次%v,", baseObj.LineId, nextObj.LineId, duplicatedbs,
						duplicatedbs))
				}
			}
		}
	}
	return errors.Join(errs...)
}

// Init init
func (e *ExecuteSQLFileComp) Init() (err error) {
	e.cleanHistorySQLDir()
	e.ports = make([]int, len(e.Params.Ports))
	e.dbConns = make(map[int]*native.DbWorker)
	e.vermap = make(map[int]string)
	e.socketmap = make(map[int]string)
	e.charsetmap = make(map[int]string)

	copy(e.ports, e.Params.Ports)
	for _, port := range e.ports {
		var ver, charset, socket string
		dbConn, err := native.InsObject{
			Host: e.Params.Host,
			Port: port,
			User: e.GeneralParam.RuntimeAccountParam.AdminUser,
			Pwd:  e.GeneralParam.RuntimeAccountParam.AdminPwd,
		}.Conn()
		if err != nil {
			logger.Error("Connect %d failed:%s", port, err.Error())
			return err
		}
		if ver, err = dbConn.SelectVersion(); err != nil {
			logger.Error("获取实例版本失败:%s", err.Error())
			return err
		}

		charset = e.Params.CharSet
		if e.Params.CharSet == cst.DefaultCharset {
			if charset, err = dbConn.ShowServerCharset(); err != nil {
				logger.Error("获取实例的字符集失败：%s", err.Error())
				return err
			}
		}
		if socket, err = dbConn.ShowSocket(); err != nil {
			logger.Error("获取socket value 失败:%s", err.Error())
			return err
		}
		if !cmutil.FileExists(socket) {
			socket = ""
		}

		e.dbConns[port] = dbConn
		e.vermap[port] = ver
		e.socketmap[port] = socket
		e.charsetmap[port] = charset
		e.taskdir = strings.TrimSpace(e.Params.FilePath)
		if e.taskdir == "" {
			e.taskdir = cst.BK_PKG_INSTALL_PATH
		}
	}
	return nil
}

// Execute execute
func (e *ExecuteSQLFileComp) Execute() (err error) {
	defer e.closeDb()
	for _, port := range e.ports {
		if err = e.executeOne(port); err != nil {
			logger.Error("execute at %d failed: %s", port, err.Error())
			return err
		}
	}
	return nil
}

func (e *ExecuteSQLFileComp) closeDb() {
	for _, port := range e.ports {
		if dbConn, ok := e.dbConns[port]; ok {
			dbConn.Close()
		}
	}
}

// OpenDdlExecuteByCtl tendbcluster变更时候 sed 之前考虑是否需要保留源文件
// 此方法仅用于spider集群变更
func (e *ExecuteSQLFileComp) OpenDdlExecuteByCtl() (err error) {
	for _, f := range e.Params.ExecuteObjects {
		for _, sqlFile := range f.SQLFiles {
			stdout, err := osutil.StandardShellCommand(
				false,
				fmt.Sprintf(`sed -i '1 i\/*!50600 SET ddl_execute_by_ctl=1*/;' %s`, path.Join(e.taskdir, sqlFile)),
			)
			if err != nil {
				logger.Error("sed insert ddl_execute_by_ctl failed %s,stdout:%s", err.Error(), stdout)
				return err
			}
			logger.Info("sed at %s,stdout:%s", sqlFile, stdout)
		}
	}
	return
}

// executeOne 执行导入SQL文件
//
//	@receiver e
//	@return err
func (e *ExecuteSQLFileComp) executeOne(port int) (err error) {
	alldbs, err := e.dbConns[port].ShowDatabases()
	if err != nil {
		logger.Error("获取实例db list失败:%s", err.Error())
		return err
	}
	dbsExcluesysdbs := util.FilterOutStringSlice(alldbs, computil.GetGcsSystemDatabasesIgnoreTest(e.vermap[port]))
	for _, f := range e.Params.ExecuteObjects {
		var realexcutedbs, intentionDbs, ignoreDbs []string
		// 获得目标库 因为是通配符 所以需要获取完整名称
		intentionDbs, err = e.match(dbsExcluesysdbs, f.parseDbParamRe())
		if err != nil {
			return err
		}
		// 获得忽略库
		ignoreDbs, err = e.match(dbsExcluesysdbs, f.parseIgnoreDbParamRe())
		if err != nil {
			return err
		}
		// 获取最终需要执行的库
		realexcutedbs = util.FilterOutStringSlice(intentionDbs, ignoreDbs)
		if len(realexcutedbs) == 0 {
			return fmt.Errorf("没有适配到任何db")
		}
		logger.Info("will real excute on %v", realexcutedbs)
		for _, sqlFile := range f.SQLFiles {
			err = mysqlutil.ExecuteSqlAtLocal{
				IsForce:          e.Params.Force,
				Charset:          e.charsetmap[port],
				NeedShowWarnings: false,
				Host:             e.Params.Host,
				Port:             port,
				Socket:           e.socketmap[port],
				WorkDir:          e.taskdir,
				User:             e.GeneralParam.RuntimeAccountParam.AdminUser,
				Password:         e.GeneralParam.RuntimeAccountParam.AdminPwd,
			}.ExecuteSqlByMySQLClient(sqlFile, realexcutedbs)
			if err != nil {
				logger.Error("执行%s文件失败:%s", sqlFile, err.Error())
				return err
			}
		}
	}
	return err
}

// match 根据show databases 返回的实际db,匹配出dbname
//
//	@receiver e
//	@receiver regularDbNames
//	@return matched
func (e *ExecuteSQLFileComp) match(dbsExculeSysdb, regularDbNames []string) (matched []string, err error) {
	for _, regexpStr := range regularDbNames {
		re, err := regexp.Compile(regexpStr)
		if err != nil {
			logger.Error(" regexp.Compile(%s) failed:%s", regexpStr, err.Error())
			return nil, err
		}
		for _, db := range dbsExculeSysdb {
			if re.MatchString(db) {
				matched = append(matched, db)
			}
		}
	}
	return
}

// parseDbParamRe TODO
// ConvertDbParamToRegular 解析DbNames参数成正则参数
//
//	@receiver e
func (e *ExecuteSQLFileObj) parseDbParamRe() (s []string) {
	return changeToMatch(e.DbNames)
}

// parseIgnoreDbParamRe  解析IgnoreDbNames参数成正则参数
//
//	@receiver e
//	@return []string
func (e *ExecuteSQLFileObj) parseIgnoreDbParamRe() (s []string) {
	return changeToMatch(e.IgnoreDbNames)
}

// changeToMatch 将输入的参数转成正则匹配的格式
//
//	@receiver input
//	@return []string
func changeToMatch(input []string) []string {
	var result []string
	for _, str := range input {
		str = strings.ReplaceAll(str, "?", ".")
		str = strings.ReplaceAll(str, "%", ".*")
		str = `^` + str + `$`
		result = append(result, str)
	}
	return result
}
