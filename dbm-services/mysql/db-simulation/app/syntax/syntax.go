/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package syntax sql syntax
package syntax

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"runtime/debug"
	"slices"
	"strings"
	"sync"
	"time"

	"github.com/samber/lo"

	"dbm-services/common/go-pubpkg/bkrepo"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app"
	"dbm-services/mysql/db-simulation/app/config"
	"dbm-services/mysql/db-simulation/model"
)

// CheckSyntax 语法检查
type CheckSyntax interface {
	Do() (result map[string]*CheckInfo, err error)
}

// TmysqlParseSQL execution parsing sql
type TmysqlParseSQL struct {
	TmysqlParse
	Sqls []string `json:"sqls"` // SQL文件名称
}

// TmysqlParseFile execution parsing sql file
type TmysqlParseFile struct {
	TmysqlParse
	Param CheckSQLFileParam
	// IsLocalFile 如果是传参是SQL语句的化，会在本地生成文件，无需下载
	IsLocalFile bool
}

// CheckSQLFileParam TODO
type CheckSQLFileParam struct {
	BkBizID        int                 `json:"bk_biz_id"`
	ClusterType    string              `json:"cluster_type"`
	BkRepoBasePath string              `json:"bkrepo_base_path"`
	FileNames      []string            `json:"file_names"`
	ExecuteObjects []ExecuteSQLFileObj `json:"execute_objects"`
}

// ExecuteSQLFileObj SQL导入执行对象
type ExecuteSQLFileObj struct {
	LineId        int      `json:"line_id"`
	SQLFiles      []string `json:"sql_files"`      // 变更文件名称
	IgnoreDbNames []string `json:"ignore_dbnames"` // 忽略的,需要排除变更的dbName,支持模糊匹配
	DbNames       []string `json:"dbnames"`        // 需要变更的DBNames,支持模糊匹配
}

// TmysqlParse TODO
type TmysqlParse struct {
	tmpWorkdir         string
	result             map[string]*CheckInfo
	bkRepoClient       *bkrepo.BkRepoClient
	TmysqlParseBinPath string
	BaseWorkdir        string
	mu                 sync.Mutex
	TendbClusterSyntaxCheckOptions
}

// TendbClusterSyntaxCheckOptions tendbcluster集群语法检查选项
type TendbClusterSyntaxCheckOptions struct {
	FastCheckMap     map[string]struct{}
	AllowProcedureOp bool `json:"allow_procedure_op"` // 允许操作存储过程
	AllowEventOp     bool `json:"allow_event_op"`     // 允许操作事件
	AllowFunctionOp  bool `json:"allow_function_op"`  // 允许操作函数
	AllowTriggerOp   bool `json:"allow_trigger_op"`   // 允许操作触发器
	AllowViewOp      bool `json:"allow_view_op"`      // 允许操作视图
	AllowAlterDbOp   bool `json:"allow_alter_db_op"`  // 允许操作数据库
	AllowFlushOp     bool `json:"allow_flush_op"`     // 允许操作flush
}

// IsDisabledOperation 检查是否禁止操作
func (tc *TendbClusterSyntaxCheckOptions) IsDisabledOperation(command_type string) bool {
	switch command_type {
	case SQLTypeCreateProcedure, SQLTypeDropProcedure:
		return !tc.AllowProcedureOp
	case SQLTypeCreateEvent, SQLTypeDropEvent:
		return !tc.AllowEventOp
	case SQLTypeCreateFunction, SQLTypeDropFunction:
		return !tc.AllowFunctionOp
	case SQLTypeCreateTrigger, SQLTypeDropTrigger:
		return !tc.AllowTriggerOp
	case SQLTypeCreateView, SQLTypeDropView:
		return !tc.AllowViewOp
	case SQLTypeAlterDb:
		return !tc.AllowAlterDbOp
	case SQLTypeFlush:
		return !tc.AllowFlushOp
	}
	return false
}

// InitTendbClusterSyntaxCheckOptions 初始化tendbcluster集群语法检查选项
func (tf *TmysqlParseFile) InitTendbClusterSyntaxCheckOptions() {
	tf.TendbClusterSyntaxCheckOptions = TendbClusterSyntaxCheckOptions{
		AllowProcedureOp: false,
		AllowEventOp:     false,
		AllowFunctionOp:  false,
		AllowTriggerOp:   false,
		AllowViewOp:      false,
		FastCheckMap:     make(map[string]struct{}),
	}
	tf.TendbClusterSyntaxCheckOptions.FastCheckMap[SQLTypeCreateProcedure] = struct{}{}
	tf.TendbClusterSyntaxCheckOptions.FastCheckMap[SQLTypeDropProcedure] = struct{}{}
	tf.TendbClusterSyntaxCheckOptions.FastCheckMap[SQLTypeCreateEvent] = struct{}{}
	tf.TendbClusterSyntaxCheckOptions.FastCheckMap[SQLTypeDropEvent] = struct{}{}
	tf.TendbClusterSyntaxCheckOptions.FastCheckMap[SQLTypeCreateFunction] = struct{}{}
	tf.TendbClusterSyntaxCheckOptions.FastCheckMap[SQLTypeDropFunction] = struct{}{}
	tf.TendbClusterSyntaxCheckOptions.FastCheckMap[SQLTypeCreateTrigger] = struct{}{}
	tf.TendbClusterSyntaxCheckOptions.FastCheckMap[SQLTypeCreateView] = struct{}{}
	tf.TendbClusterSyntaxCheckOptions.FastCheckMap[SQLTypeDropTrigger] = struct{}{}
	tf.TendbClusterSyntaxCheckOptions.FastCheckMap[SQLTypeDropView] = struct{}{}
	tf.TendbClusterSyntaxCheckOptions.FastCheckMap[SQLTypeFlush] = struct{}{}
	tf.TendbClusterSyntaxCheckOptions.FastCheckMap[SQLTypeAlterDb] = struct{}{}
	if tf.Param.BkBizID <= 0 {
		return
	}
	bizIds, err := model.GetWhitelistBizIds(app.TendbCluster)
	if err != nil {
		logger.Error("get whitelist biz ids failed %s", err.Error())
		return
	}
	if lo.Contains(bizIds, tf.Param.BkBizID) {
		tf.TendbClusterSyntaxCheckOptions.AllowProcedureOp = true
		tf.TendbClusterSyntaxCheckOptions.AllowEventOp = true
		tf.TendbClusterSyntaxCheckOptions.AllowFunctionOp = true
		tf.TendbClusterSyntaxCheckOptions.AllowTriggerOp = true
		tf.TendbClusterSyntaxCheckOptions.AllowViewOp = true
		tf.TendbClusterSyntaxCheckOptions.AllowAlterDbOp = true
		tf.TendbClusterSyntaxCheckOptions.AllowFlushOp = true
		return
	}
}

// AddFileResult add file syntax check result
func (t *TmysqlParse) AddFileResult(fileName string, result *CheckInfo, failedInfos []FailedInfo) {
	t.mu.Lock()
	if _, ok := t.result[fileName]; !ok {
		t.result[fileName] = result
		t.result[fileName].SyntaxFailInfos = failedInfos
	} else {
		t.result[fileName].SyntaxFailInfos = append(t.result[fileName].SyntaxFailInfos, failedInfos...)
	}
	t.result[fileName].BanWarnings = result.BanWarnings
	t.result[fileName].RiskWarnings = result.RiskWarnings
	t.mu.Unlock()
}

// CheckInfo 语法检查结果信息汇总
type CheckInfo struct {
	SyntaxFailInfos []FailedInfo `json:"syntax_fails"`
	RiskWarnings    []RiskInfo   `json:"highrisk_warnings"`
	BanWarnings     []RiskInfo   `json:"bancommand_warnings"`
}

// FailedInfo 语法错误结果
type FailedInfo struct {
	Sqltext   string `json:"sqltext"`
	ErrorMsg  string `json:"error_msg"`
	Line      int64  `json:"line"`
	ErrorCode int64  `json:"error_code"`
}

// RiskInfo 高危语句结果
type RiskInfo struct {
	CommandType string `json:"command_type"`
	Sqltext     string `json:"sqltext"`
	WarnInfo    string `json:"warn_info"`
	Line        int64  `json:"line"`
}

// DdlMapFileSubffix  execution parsing sql provisional results document
const DdlMapFileSubffix = ".tbl.map"

// RunSyntaxCheck 运行语法检查
func (tf *TmysqlParseFile) RunSyntaxCheck(versions []string) (result map[string]*CheckInfo, err error) {
	var data map[string]*CheckInfo
	logger.Info("cluster type :%s", tf.Param.ClusterType)
	switch strings.ToLower(tf.Param.ClusterType) {
	case app.Spider, app.TendbCluster:
		tf.InitTendbClusterSyntaxCheckOptions()
		data, err = tf.Do(app.Spider, []string{""})
	case app.MySQL:
		data, err = tf.Do(app.MySQL, versions)
	default:
		data, err = tf.Do(app.MySQL, versions)
	}
	return data, err
}

// Do  运行语法检查 For SQL 文件
func (tf *TmysqlParseFile) Do(dbtype string, versions []string) (result map[string]*CheckInfo, err error) {
	tf.mu = sync.Mutex{}
	tf.mu.Lock()
	tf.result = make(map[string]*CheckInfo)
	tf.tmpWorkdir = tf.BaseWorkdir
	tf.mu.Unlock()
	if !tf.IsLocalFile {
		if err = tf.Init(); err != nil {
			logger.Error("Do init failed %s", err.Error())
			return nil, err
		}
		if err = tf.Downloadfile(); err != nil {
			logger.Error("failed to download sql file from the product library %s", err.Error())
			return nil, err
		}
	}
	// 最后删除临时目录,不会返回错误
	defer tf.DelTempDir()

	var errs []error
	for _, version := range versions {
		if err = tf.doSingleVersion(dbtype, version); err != nil {
			logger.Error("when do [%s],syntax check,failed:%s", version, err.Error())
			errs = append(errs, err)
		}
	}
	// check input db conflict with use db
	if err = tf.CheckConflictUsedb(versions[0]); err != nil {
		logger.Error("check conflict usedb failed %s", err.Error())
		errs = append(errs, err)
	}
	return tf.result, errors.Join(errs...)
}

// CheckSystemDBOperation 检查系统库操作
// 如果执行对象是系统库，则检查文件的第一行
// 如果第一行命令不是 USE DB 或 CREATE DATABASE，则追加警告信息
func (tf *TmysqlParseFile) CheckSystemDBOperation(version string) error {
	for _, executeObject := range tf.Param.ExecuteObjects {
		if len(executeObject.DbNames) == 0 {
			continue
		}
		// 检查目标是否为系统库
		targetIsSysDb := false
		sysdbs := cmutil.GetGcsSystemDatabases(version)
		for _, db := range executeObject.DbNames {
			if lo.Contains(sysdbs, db) {
				targetIsSysDb = true
				break
			}
		}
		// 如果不是系统库，跳过检查
		if !targetIsSysDb {
			continue
		}

		// 检查每个 SQL 文件的第一行
		for _, sqlFile := range executeObject.SQLFiles {
			// 初始化结果（如果不存在）
			if tf.result[sqlFile] == nil {
				tf.result[sqlFile] = &CheckInfo{}
			}
			// 如果语法检查都是错误的 就不用分析了
			// 因为无法解析sql里面的真是dbname
			if len(tf.result[sqlFile].SyntaxFailInfos) > 0 {
				continue
			}

			f, err := os.Open(tf.getAbsOutputFilePath(sqlFile, version))
			if err != nil {
				logger.Error("open file failed %s", err.Error())
				return err
			}
			defer f.Close()
			reader := bufio.NewReader(f)
			for {
				line, isPrefix, errx := reader.ReadLine()
				if errx != nil {
					if errx == io.EOF {
						break
					}
					logger.Error("read Line Error %s", errx.Error())
					return errx
				}
				var buf []byte
				buf = append(buf, line...)
				for isPrefix {
					line, isPrefix, errx = reader.ReadLine()
					if errx != nil {
						logger.Error("read Line Error %s", errx.Error())
						return errx
					}
					buf = append(buf, line...)
				}
				bs := buf

				if len(bs) == 0 {
					logger.Info("blank line skip")
					continue
				}
				var res ParseLineQueryBase
				if err = json.Unmarshal(bs, &res); err != nil {
					logger.Error("json unmarshal line:%s failed %s", string(bs), err.Error())
					return err
				}
				if res.Command == SQLTypeSetOption {
					continue
				}
				if res.Command == SQLTypeUseDb && cmutil.ElementNotInArry(res.DbName, sysdbs) {
					break
				}
				if res.Command == "" && res.DbName == "" && res.QueryId == 0 {
					//  处理最后一行的数据
					// {
					// 	"min_mysql_version": null,
					// 	"max_mysql_version": null
					//   }
					break
				}
				// 检查命令类型
				logger.Info("bs:%s,res.Command:%s,res.DbName:%s", string(bs), res.Command, res.DbName)
				if cmutil.ElementNotInArry(res.Command, []string{SQLTypeCreateDb, SQLTypeUseDb}) &&
					(res.DbName == "" || slices.Contains(sysdbs, res.DbName)) {
					tf.result[sqlFile].BanWarnings = append(tf.result[sqlFile].BanWarnings, RiskInfo{
						Line:     int64(res.QueryId),
						Sqltext:  res.QueryString,
						WarnInfo: fmt.Sprintf("不允许直接在系统库%v,操作", executeObject.DbNames),
					})
				}
			}
		}
	}
	return nil
}

// CheckConflictUsedb check input db conflict with use db
func (tf *TmysqlParseFile) CheckConflictUsedb(version string) (err error) {
	// 先检查系统库操作
	if err = tf.CheckSystemDBOperation(version); err != nil {
		logger.Error("check system db operation failed %s", err.Error())
		return err
	}

	for _, executeObject := range tf.Param.ExecuteObjects {
		if len(executeObject.DbNames) == 0 {
			continue
		}
		if len(executeObject.DbNames) == 1 && !strings.Contains(executeObject.DbNames[0], "%") &&
			!strings.Contains(executeObject.DbNames[0], "?") {
			continue
		}
		var buf []byte
		for _, sqlFile := range executeObject.SQLFiles {
			f, err := os.Open(tf.getAbsOutputFilePath(sqlFile, version))
			if err != nil {
				logger.Error("open file failed %s", err.Error())
				return err
			}
			defer f.Close()
			reader := bufio.NewReader(f)
			for {
				line, isPrefix, errx := reader.ReadLine()
				if errx != nil {
					if errx == io.EOF {
						break
					}
					logger.Error("read Line Error %s", errx.Error())
					return errx
				}
				buf = append(buf, line...)
				if isPrefix {
					continue
				}
				bs := buf
				buf = []byte{}
				var res ParseLineQueryBase
				if len(bs) == 0 {
					logger.Info("blank line skip")
					continue
				}
				if err = json.Unmarshal(bs, &res); err != nil {
					logger.Error("json unmarshal line:%s failed %s", string(bs), err.Error())
					return err
				}

				if res.Command == SQLTypeUseDb {
					tf.result[sqlFile].BanWarnings = append(tf.result[sqlFile].BanWarnings, RiskInfo{
						Line:    int64(res.QueryId),
						Sqltext: res.QueryString,
						WarnInfo: fmt.Sprintf("表单中输入的变更对象%v可能存在多个,但是SQL文件显示的使用use %s,可能会造成SQL文件重复执行,请正确理解表单语义,修改后在提交",
							executeObject.DbNames,
							res.DbName),
					})
					return nil
				}
			}
		}
	}
	return nil
}

func (tf *TmysqlParseFile) doSingleVersion(dbtype string, mysqlVersion string) (err error) {
	errChan := make(chan error)
	ExecutedSqlFileChan := make(chan string, len(tf.Param.FileNames))
	signalChan := make(chan struct{})

	go func() {
		if err = tf.Execute(ExecutedSqlFileChan, mysqlVersion); err != nil {
			logger.Error("failed to execute tmysqlparse: %s", err.Error())
			errChan <- err
		}
		close(ExecutedSqlFileChan)
	}()

	// 对tmysqlparse的处理结果进行分析，为json文件，后面用到了rule
	go func() {
		logger.Info("start to analyze the parsing result")
		if err = tf.AnalyzeParseResult(ExecutedSqlFileChan, mysqlVersion, dbtype); err != nil {
			logger.Error("failed to analyze the parsing result:%s", err.Error())
			errChan <- err
		}
		signalChan <- struct{}{}
	}()

	select {
	case err := <-errChan:
		logger.Error("failed to do sytax check:%s", err.Error())
		return err
	case <-signalChan:
		logger.Info("analyze the parsing result done")
		break
	}
	return nil
}

// CreateAndUploadDDLTblFile CreateAndUploadDDLTblFile
func (tf *TmysqlParseFile) CreateAndUploadDDLTblFile() (err error) {
	logger.Info("start to create and upload ddl table file")
	if err = tf.Init(); err != nil {
		logger.Error("Do init failed %s", err.Error())
		return err
	}
	// 最后删除临时目录,不会返回错误
	// 暂时屏蔽 观察过程文件
	defer tf.DelTempDir()

	if err = tf.Downloadfile(); err != nil {
		logger.Error("failed to download sql file from the product library %s", err.Error())
		return err
	}
	errChan := make(chan error)
	resultFileChan := make(chan string, 10)
	go func() {
		if err = tf.Execute(resultFileChan, ""); err != nil {
			logger.Error("failed to execute tmysqlparse: %s", err.Error())
			errChan <- err
			//	return nil, err
		}
		close(resultFileChan)
	}()

	for inputFileName := range resultFileChan {
		if err = tf.analyzeDDLTbls(inputFileName, ""); err != nil {
			logger.Error("failed to analyzeDDLTbls %s,err:%s", inputFileName, err.Error())
			return err
		}
	}
	if err = tf.UploadDdlTblMapFile(); err != nil {
		logger.Error("failed to upload ddl table file %s", err.Error())
		return err
	}
	return nil
}

var bkrepoClient *bkrepo.BkRepoClient
var once sync.Once

func getBkrepoClient() *bkrepo.BkRepoClient {
	once.Do(func() {
		bkrepoClient = &bkrepo.BkRepoClient{
			Client: &http.Client{
				Transport: &http.Transport{},
			},
			BkRepoProject:   config.GAppConfig.BkRepo.Project,
			BkRepoPubBucket: config.GAppConfig.BkRepo.PublicBucket,
			BkRepoUser:      config.GAppConfig.BkRepo.User,
			BkRepoPwd:       config.GAppConfig.BkRepo.Pwd,
			BkRepoEndpoint:  config.GAppConfig.BkRepo.EndPointUrl,
		}
		logger.Info("once get config")
	})
	return bkrepoClient
}

// Init init env
func (t *TmysqlParse) Init() (err error) {
	tmpDir := fmt.Sprintf("tmysqlparse_%s_%s", time.Now().Format("20060102150405"), lo.RandomString(6,
		[]rune("0123456789abcdefghijklmnopqrstuvwxyz")))
	t.tmpWorkdir = path.Join(t.BaseWorkdir, tmpDir)
	if err = os.MkdirAll(t.tmpWorkdir, os.ModePerm); err != nil {
		logger.Error("mkdir %s failed, err:%+v", t.tmpWorkdir, err)
		return fmt.Errorf("failed to initialize tmysqlparse temporary directory(%s).detail:%s", t.tmpWorkdir, err.Error())
	}
	t.bkRepoClient = getBkrepoClient()
	t.result = make(map[string]*CheckInfo)
	return nil
}

// DelTempDir del tempDir
func (t *TmysqlParse) DelTempDir() {
	logger.Info("start to remove tempDir:%s", t.tmpWorkdir)
	if err := os.RemoveAll(t.tmpWorkdir); err != nil {
		logger.Warn("remove tempDir:" + t.tmpWorkdir + ".error info:" + err.Error())
	}
}

// Downloadfile download sqlfile
func (tf *TmysqlParseFile) Downloadfile() (err error) {
	wg := &sync.WaitGroup{}
	errCh := make(chan error)
	c := make(chan struct{}, 5)
	for _, fileName := range tf.Param.FileNames {
		wg.Add(1)
		go func(fileName string) {
			c <- struct{}{}
			defer func() { wg.Done(); <-c }()
			err = tf.bkRepoClient.Download(tf.Param.BkRepoBasePath, fileName, tf.tmpWorkdir)
			if err != nil {
				logger.Error("download %s from bkrepo failed :%s", fileName, err.Error())
				errCh <- err
			}
		}(fileName)
	}
	go func() {
		wg.Wait()
		close(errCh)
	}()
	var errs []error
	for errx := range errCh {
		errs = append(errs, errx)
	}
	return errors.Join(errs...)
}

// UploadDdlTblMapFile upload analyze ddl tables
func (tf *TmysqlParseFile) UploadDdlTblMapFile() (err error) {
	for _, fileName := range tf.Param.FileNames {
		ddlTblFile := fileName + DdlMapFileSubffix
		resp, err := tf.bkRepoClient.Upload(path.Join(tf.tmpWorkdir, ddlTblFile), ddlTblFile,
			tf.Param.BkRepoBasePath)
		if err != nil {
			logger.Error("download %s from bkrepo failed :%s", fileName, err.Error())
			return err
		}
		if resp.Code != 0 {
			logger.Warn("upload ddl table map file for %s failed,msg:%s,cod:%d", fileName, resp.Message, resp.Code)
		}
	}
	return
}

func getSQLParseResultFile(fileName, version string) string {
	if lo.IsNotEmpty(version) {
		return fmt.Sprintf("%s-%s.json", version, fileName)
	}
	return fileName + ".json"
}

// getCommand generates the command string for running TmysqlParse
// It takes the input filename and MySQL version as parameters
func (t *TmysqlParse) getCommand(filename, version string) string {
	// Construct input and output file paths
	inputPath := path.Join(t.tmpWorkdir, filename)
	outputFileName := getSQLParseResultFile(filename, version)
	outputPath := path.Join(t.tmpWorkdir, outputFileName)

	// Build the base command with common options
	cmd := fmt.Sprintf(`%s --sql-file=%s --output-path=%s `+
		`--print-query-mode=2 --output-format='JSON_LINE_PER_OBJECT' --sql-mode=''`,
		t.TmysqlParseBinPath, inputPath, outputPath)

	// Add MySQL version if provided
	if lo.IsNotEmpty(version) {
		cmd += fmt.Sprintf(" --mysql-version=%s", version)
	}

	return cmd
}

// Execute runs the TmysqlParse command for each SQL file in parallel.
// It takes a channel to send the names of successfully executed files and the MySQL version as parameters.
// The function returns an error if any of the executions fail.
func (tf *TmysqlParseFile) Execute(executedSqlFileCh chan string, version string) (err error) {
	var wg sync.WaitGroup
	var errs []error
	c := make(chan struct{}, 10) // Semaphore to limit concurrent goroutines
	errChan := make(chan error)

	// Iterate through all SQL files
	for _, fileName := range tf.Param.FileNames {
		wg.Add(1)
		go func(sqlfile, ver string) {
			c <- struct{}{}
			defer func() { <-c; wg.Done() }()
			//nolint
			command := exec.Command("/bin/bash", "-c", tf.getCommand(sqlfile, ver))
			logger.Info("command is %s", command)

			output, err := command.CombinedOutput()
			if err != nil {
				errChan <- fmt.Errorf("tmysqlparse.sh command run failed. error info: %v, %s", err, string(output))
			} else {
				executedSqlFileCh <- sqlfile
			}
		}(fileName, version)
	}

	// Wait for all goroutines to finish and close error channel
	go func() {
		wg.Wait()
		close(errChan)
	}()

	// Collect all errors
	for err := range errChan {
		errs = append(errs, err)
	}

	// Join all errors and return
	return errors.Join(errs...)
}

func (t *TmysqlParse) getAbsOutputFilePath(sqlFile, version string) string {
	fileAbPath, _ := filepath.Abs(path.Join(t.tmpWorkdir, getSQLParseResultFile(sqlFile, version)))
	return fileAbPath
}

// AnalyzeParseResult 分析tmysqlparse 解析的结果
func (t *TmysqlParse) AnalyzeParseResult(executedSqlFileCh chan string, mysqlVersion string,
	dbtype string) (err error) {
	var errs []error
	c := make(chan struct{}, 10)
	errChan := make(chan error)
	wg := &sync.WaitGroup{}

	for sqlfile := range executedSqlFileCh {
		wg.Add(1)
		go func(fileName string) {
			c <- struct{}{}
			defer wg.Done()
			err = t.AnalyzeOne(fileName, mysqlVersion, dbtype)
			if err != nil {
				errChan <- err
			}
			<-c
		}(sqlfile)
	}

	go func() {
		wg.Wait()
		close(errChan)
	}()

	for err := range errChan {
		errs = append(errs, err)
	}

	return errors.Join(errs...)
}

func (c *CheckInfo) parseResult(rule *RuleItem, res ParseLineQueryBase, ver string) {
	matched, err := rule.CheckItem(res.Command)
	if matched {
		if rule.Ban {
			c.BanWarnings = append(c.BanWarnings, RiskInfo{
				Line:        int64(res.QueryId),
				Sqltext:     res.QueryString,
				CommandType: res.Command,
				WarnInfo:    fmt.Sprintf("[%s]: %s", ver, err.Error()),
			})
		} else {
			c.RiskWarnings = append(c.RiskWarnings, RiskInfo{
				Line:        int64(res.QueryId),
				Sqltext:     res.QueryString,
				CommandType: res.Command,
				WarnInfo:    fmt.Sprintf("[%s]: %s", ver, err.Error()),
			})
		}
	}
}

// analyzeDDLTbls 分析DDL语句
func (t *TmysqlParse) analyzeDDLTbls(inputFileName, mysqlVersion string) (err error) {
	ddlTbls := make(map[string][]string)
	defer func() {
		if r := recover(); r != nil {
			logger.Error("panic error:%v,stack:%s", r, string(debug.Stack()))
		}
	}()
	t.result[inputFileName] = &CheckInfo{}
	f, err := os.Open(t.getAbsOutputFilePath(inputFileName, mysqlVersion))
	if err != nil {
		logger.Error("open file failed %s", err.Error())
		return err
	}
	defer f.Close()
	reader := bufio.NewReader(f)
	for {
		line, errx := reader.ReadBytes(byte('\n'))
		if errx != nil {
			if errx == io.EOF {
				break
			}
			logger.Error("read Line Error %s", errx.Error())
			return errx
		}
		if len(line) == 1 && line[0] == byte('\n') {
			continue
		}
		var res ParseLineQueryBase
		if err = json.Unmarshal(line, &res); err != nil {
			logger.Error("json unmarshal line:%s failed %s", string(line), err.Error())
			return err
		}
		// 判断是否有语法错误
		if res.ErrorCode != 0 {
			return err
		}
		switch res.Command {
		case SQLTypeCreateTable, SQLTypeAlterTable:
			var o CommDDLResult
			if err = json.Unmarshal(line, &o); err != nil {
				logger.Error("json unmarshal line failed %s", err.Error())
				return err
			}
			// 如果dbname为空，则实际库名由参数指定,无特殊情况
			ddlTbls[o.DbName] = append(ddlTbls[o.DbName], o.TableName)
		}
	}
	fd, err := os.Create(path.Join(t.tmpWorkdir, inputFileName+DdlMapFileSubffix))
	if err != nil {
		logger.Error("create file failed %s", err.Error())
		return err
	}
	defer fd.Close()
	b, err := json.Marshal(ddlTbls)
	if err != nil {
		logger.Error("json marshal failed %s", err.Error())
		return err
	}
	_, err = fd.Write(b)
	if err != nil {
		logger.Error("write file failed %s", err.Error())
		return err
	}
	return nil
}

// getSyntaxErrorResult  with syntax error result
func (t *TmysqlParse) getSyntaxErrorResult(res ParseLineQueryBase, mysqlVersion string) FailedInfo {
	errMsg := res.ErrorMsg
	vl := strings.Split(mysqlVersion, ".")
	if len(vl) >= 2 {
		errMsg = fmt.Sprintf("[%s]: %s", fmt.Sprintf("MySQL-%s.%s", vl[0], vl[1]), res.ErrorMsg)
	}
	return FailedInfo{
		Line:      int64(res.QueryId),
		Sqltext:   res.QueryString,
		ErrorCode: int64(res.ErrorCode),
		ErrorMsg:  errMsg,
	}
}

// AnalyzeOne 分析单个文件
func (t *TmysqlParse) AnalyzeOne(inputfileName, mysqlVersion, dbtype string) (err error) {
	var idx int
	var syntaxFailInfos []FailedInfo
	var buf []byte
	ddlTbls := make(map[string][]string)
	checkResult := &CheckInfo{}

	f, err := os.Open(t.getAbsOutputFilePath(inputfileName, mysqlVersion))
	if err != nil {
		logger.Error("open file failed %s", err.Error())
		return err
	}
	defer f.Close()

	reader := bufio.NewReader(f)
	for {
		idx++
		line, isPrefix, errx := reader.ReadLine()
		if errx != nil {
			if errx == io.EOF {
				break
			}
			logger.Error("read Line Error %s", errx.Error())
			return errx
		}
		buf = append(buf, line...)
		if isPrefix {
			continue
		}
		bs := buf
		buf = []byte{}

		var res ParseLineQueryBase
		if len(bs) == 0 {
			logger.Info("blank line skip")
			continue
		}
		if err = json.Unmarshal(bs, &res); err != nil {
			logger.Error("json unmarshal line:%s failed %s", string(bs), err.Error())
			return err
		}
		//  ErrorCode !=0 就是语法错误
		if res.ErrorCode != 0 {
			syntaxFailInfos = append(syntaxFailInfos, t.getSyntaxErrorResult(res, mysqlVersion))
			continue
		}
		// 判断是否变更的是系统数据库
		if res.IsSysDb() {
			t.mu.Lock()
			checkResult.BanWarnings = append(checkResult.BanWarnings, RiskInfo{
				Line:     int64(res.QueryId),
				Sqltext:  res.QueryString,
				WarnInfo: fmt.Sprintf("禁止操作系统库: %s", res.DbName),
			})
			t.mu.Unlock()
			continue
		}
		// tmysqlparse检查结果全部正确，开始判断语句是否符合定义的规则（即虽然语法正确，但语句可能是高危语句或禁用的命令）
		switch dbtype {
		case app.MySQL:
			checkResult.parseResult(R.CommandRule.HighRiskCommandRule, res, mysqlVersion)
			checkResult.parseResult(R.CommandRule.BanCommandRule, res, mysqlVersion)
			err = checkResult.runcheck(res, bs, mysqlVersion)
			if err != nil {
				goto END
			}
		case app.Spider:
			if _, ok := t.TendbClusterSyntaxCheckOptions.FastCheckMap[res.Command]; ok {
				if t.IsDisabledOperation(res.Command) {
					checkResult.BanWarnings = append(checkResult.BanWarnings, RiskInfo{
						Line:        int64(res.QueryId),
						Sqltext:     res.QueryString,
						CommandType: res.Command,
						WarnInfo:    fmt.Sprintf("禁止操作: %s,需要开始请找DBA协商", res.Command),
					})
					continue
				}
			}
			checkResult.parseResult(SR.CommandRule.HighRiskCommandRule, res, mysqlVersion)
			checkResult.parseResult(SR.CommandRule.BanCommandRule, res, mysqlVersion)
			err = checkResult.runSpidercheck(ddlTbls, res, bs, mysqlVersion)
			if err != nil {
				goto END
			}
		}
	}
END:
	if err != nil {
		logger.Error("run check failed %v", err)
	}
	t.AddFileResult(inputfileName, checkResult, syntaxFailInfos)
	return err
}

func (c *CheckInfo) runSpidercheck(ddlTbls map[string][]string, res ParseLineQueryBase, bs []byte,
	mysqlVersion string) (err error) {
	var sc SpiderChecker
	// 其他规则分析
	logger.Info("run spider check")
	logger.Info("res: %+v", res)
	switch res.Command {
	case SQLTypeCreateTable:
		var o CreateTableResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmarshal line failed %s", err.Error())
			return err
		}
		o.TableOptionMap = ConvertTableOptionToMap(o.TableOptions)
		sc = o
		// 如果dbName为空，则实际库名由参数指定,无特殊情况
		ddlTbls[o.DbName] = append(ddlTbls[o.DbName], o.TableName)
	case SQLTypeCreateDb:
		var o CreateDBResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmarshal line failed %s", err.Error())
			return err
		}
		sc = o
	case SQLTypeDelete:
		var o DeleteResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmarshal line failed %s", err.Error())
			return err
		}
		sc = o
	case SQLTypeUpdate:
		var o UpdateResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmarshal line failed %s", err.Error())
			return err
		}
		sc = o
	case SQLTypeCreateFunction, SQLTypeCreateTrigger, SQLTypeCreateEvent, SQLTypeCreateProcedure, SQLTypeCreateView,
		SQLTypeCreateSpFunction:
		var o DefinerBase
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmarshal line failed %s", err.Error())
			return err
		}
		sc = o
	case SQLTypeRenameTable:
		var o RenameTableResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmarshal line failed %s", err.Error())
			return err
		}
		logger.Info("===== rename table result: %+v", o)
		sc = o
	case SQLTypeAlterTable:
		var o AlterTableResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmarshal line failed %s", err.Error())
			return err
		}
		sc = o
		ddlTbls[o.DbName] = append(ddlTbls[o.DbName], o.TableName)
	}
	if sc == nil {
		return nil
	}
	// 不同结构体绑定不同的Checker
	result := sc.SpiderChecker(mysqlVersion)
	if result.IsPass() {
		return nil
	}
	if len(result.BanWarns) > 0 {
		c.BanWarnings = append(c.BanWarnings, RiskInfo{
			Line:        int64(res.QueryId),
			Sqltext:     res.QueryString,
			CommandType: res.Command,
			WarnInfo:    prettyErrorsOutput(result.BanWarns),
		})
	}
	if len(result.RiskWarns) > 0 {
		c.RiskWarnings = append(c.RiskWarnings, RiskInfo{
			Line:        int64(res.QueryId),
			Sqltext:     res.QueryString,
			CommandType: res.Command,
			WarnInfo:    prettyErrorsOutput(result.RiskWarns),
		})
	}
	return err
}

func (c *CheckInfo) runcheck(res ParseLineQueryBase, bs []byte, mysqlVersion string) (err error) {
	var mc Checker
	// 其他规则分析
	switch res.Command {
	case SQLTypeCreateTable:
		var o CreateTableResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmarshal line failed %s", err.Error())
			return err
		}
		mc = o
	case SQLTypeAlterTable:
		var o AlterTableResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmarshal line failed %s", err.Error())
			return err
		}
		mc = o
	case SQLTypeDelete:
		var o DeleteResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmarshal line failed %s", err.Error())
			return err
		}
		mc = o
	case SQLTypeUpdate:
		var o UpdateResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmarshal line failed %s", err.Error())
			return err
		}
		mc = o
	case SQLTypeCreateFunction, SQLTypeCreateTrigger, SQLTypeCreateEvent, SQLTypeCreateProcedure, SQLTypeCreateView,
		SQLTypeCreateSpFunction:
		var o DefinerBase
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmarshal line failed %s", err.Error())
			return err
		}
		mc = o
	case SQLTypeCreateDb:
		var o CreateDBResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmarshal line failed %s", err.Error())
			return err
		}
		mc = o
	}

	if mc == nil {
		return nil
	}
	// 不同结构体绑定不同的Checker
	result := mc.Checker(mysqlVersion)
	if result.IsPass() {
		return nil
	}
	if len(result.BanWarns) > 0 {
		c.BanWarnings = append(c.BanWarnings, RiskInfo{
			Line:        int64(res.QueryId),
			Sqltext:     res.QueryString,
			CommandType: res.Command,
			WarnInfo:    prettyErrorsOutput(result.BanWarns),
		})
	}
	if len(result.RiskWarns) > 0 {
		c.RiskWarnings = append(c.RiskWarnings, RiskInfo{
			Line:        int64(res.QueryId),
			Sqltext:     res.QueryString,
			CommandType: res.Command,
			WarnInfo:    prettyErrorsOutput(result.RiskWarns),
		})
	}
	return err
}

func prettyErrorsOutput(warnInfos []string) (msg string) {
	for _, v := range warnInfos {
		msg += fmt.Sprintf("%s\n", v)
	}
	return
}
