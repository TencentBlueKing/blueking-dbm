/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package syntax TODO
package syntax

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math/rand"
	"net/http"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"runtime/debug"
	"strconv"
	"sync"
	"time"

	"dbm-services/common/go-pubpkg/bkrepo"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app"
	"dbm-services/mysql/db-simulation/app/config"
)

// CheckSyntax TODO
type CheckSyntax interface {
	Do() (result map[string]*CheckInfo, err error)
}

type inputFileName = string
type outputFileName = string

// TmysqlParseSQL TODO
type TmysqlParseSQL struct {
	TmysqlParse
	Sqls []string `json:"sqls"` // SQL文件名称
}

// TmysqlParseFile TODO
type TmysqlParseFile struct {
	TmysqlParse
	Param       CheckSqlFileParam
	IsLocalFile bool
}

// CheckSqlFileParam TODO
type CheckSqlFileParam struct {
	BkRepoBasePath string   `json:"bkrepo_base_path"`
	MysqlVersion   string   `json:"mysql_version"`
	FileNames      []string `json:"file_names"`
}

// TmysqlParse TODO
type TmysqlParse struct {
	runtimeCtx
	result             map[string]*CheckInfo
	bkRepoClient       *bkrepo.BkRepoClient
	TmysqlParseBinPath string
	BaseWorkdir        string
}

type runtimeCtx struct {
	fileMap    map[inputFileName]outputFileName
	tmpWorkdir string
}

// CheckInfo TODO
type CheckInfo struct {
	SyntaxFailInfos []FailedInfo `json:"syntax_fails"`
	RiskWarnings    []RiskInfo   `json:"highrisk_warnings"`
	BanWarnings     []RiskInfo   `json:"bancommand_warnings"`
}

// FailedInfo TODO
type FailedInfo struct {
	Sqltext   string `json:"sqltext"`
	ErrorMsg  string `json:"error_msg"`
	Line      int64  `json:"line"`
	ErrorCode int64  `json:"error_code"`
}

// RiskInfo TODO
type RiskInfo struct {
	CommandType string `json:"command_type"`
	Sqltext     string `json:"sqltext"`
	WarnInfo    string `json:"warn_info"`
	Line        int64  `json:"line"`
}

// DDLMAP_FILE_SUFFIX TODO
const DDLMAP_FILE_SUFFIX = ".tbl.map"

// Do  运行语法检查 For SQL 文件
//
//	@receiver tf
//	@return result
//	@return err
func (tf *TmysqlParseFile) Do(dbtype string) (result map[string]*CheckInfo, err error) {
	logger.Info("doing....")
	tf.fileMap = make(map[inputFileName]outputFileName)
	tf.result = make(map[string]*CheckInfo)
	tf.tmpWorkdir = tf.BaseWorkdir
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
	// 暂时屏蔽 观察过程文件
	defer tf.delTempDir()
	errChan := make(chan error)
	resultfileChan := make(chan string, 10)
	signalChan := make(chan struct{})
	go func() {
		if err = tf.Execute(resultfileChan); err != nil {
			logger.Error("failed to execute tmysqlparse: %s", err.Error())
			errChan <- err
			//	return nil, err
		}
		close(resultfileChan)
	}()

	// 对tmysqlparse的处理结果进行分析，为json文件，后面用到了rule
	mysqlVersion := tf.Param.MysqlVersion

	go func() {
		logger.Info("start to analyze the parsing result")
		if err = tf.AnalyzeParseResult(resultfileChan, mysqlVersion, dbtype); err != nil {
			logger.Error("failed to analyze the parsing result:%s", err.Error())
			errChan <- err
			//	return tf.result, err
		}
		signalChan <- struct{}{}
	}()
	// 在一定程度上会增加语法检查的耗时、后续先观察一下
	// if dbtype == app.Spider {
	// 	 tf.UploadDdlTblMapFile()
	// }
	select {
	case err := <-errChan:
		return tf.result, err
	case <-signalChan:
		logger.Info("analyze the parsing result done")
		break
	}
	return tf.result, nil
}

// CreateAndUploadDDLTblFile TODO
func (tf *TmysqlParseFile) CreateAndUploadDDLTblFile() (err error) {
	logger.Info("start to create and upload ddl table file")
	logger.Info("doing....")
	if err = tf.Init(); err != nil {
		logger.Error("Do init failed %s", err.Error())
		return err
	}
	// 最后删除临时目录,不会返回错误
	// 暂时屏蔽 观察过程文件
	defer tf.delTempDir()

	if err = tf.Downloadfile(); err != nil {
		logger.Error("failed to download sql file from the product library %s", err.Error())
		return err
	}
	errChan := make(chan error)
	resultfileChan := make(chan string, 10)
	go func() {
		if err = tf.Execute(resultfileChan); err != nil {
			logger.Error("failed to execute tmysqlparse: %s", err.Error())
			errChan <- err
			//	return nil, err
		}
		close(resultfileChan)
	}()

	for inputFileName := range resultfileChan {
		if err = tf.analyzeDDLTbls(inputFileName); err != nil {
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

func getbkrepoClient() *bkrepo.BkRepoClient {
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

// Init TODO
func (t *TmysqlParse) Init() (err error) {
	tmpDir := fmt.Sprintf("tmysqlparse_%s_%s", time.Now().Format("20060102150405"), strconv.Itoa(rand.Intn(10000)))
	t.tmpWorkdir = path.Join(t.BaseWorkdir, tmpDir)
	if err = os.MkdirAll(t.tmpWorkdir, os.ModePerm); err != nil {
		logger.Error("mkdir %s failed, err:%+v", t.tmpWorkdir, err)
		return fmt.Errorf("failed to initialize tmysqlparse temporary directory(%s).detail:%s", t.tmpWorkdir, err.Error())
	}
	t.bkRepoClient = getbkrepoClient()
	t.fileMap = make(map[inputFileName]outputFileName)
	t.result = make(map[string]*CheckInfo)
	return nil
}

func (t *TmysqlParse) delTempDir() {
	if err := os.RemoveAll(t.tmpWorkdir); err != nil {
		logger.Warn("remove tempDir:" + t.tmpWorkdir + ".error info:" + err.Error())
	}
}

func (t *TmysqlParse) getCommand(filename string) (cmd string) {
	var in, out string
	in = path.Join(t.tmpWorkdir, filename)
	if outputFileName, ok := t.fileMap[filename]; ok {
		out = path.Join(t.tmpWorkdir, outputFileName)
	}
	bin := t.TmysqlParseBinPath
	return fmt.Sprintf(`%s --sql-file=%s --output-path=%s --print-query-mode=2 --output-format='JSON_LINE_PER_OBJECT'`,
		bin, in, out)
}

// Downloadfile TODO
func (tf *TmysqlParseFile) Downloadfile() (err error) {
	wg := &sync.WaitGroup{}
	errCh := make(chan error, 10)
	c := make(chan struct{}, 5)
	for _, fileName := range tf.Param.FileNames {
		wg.Add(1)
		c <- struct{}{}
		go func(fileName string) {
			defer wg.Done()
			err = tf.bkRepoClient.Download(tf.Param.BkRepoBasePath, fileName, tf.tmpWorkdir)
			if err != nil {
				logger.Error("download %s from bkrepo failed :%s", fileName, err.Error())
				errCh <- err
			}
			<-c
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

// UploadDdlTblMapFile TODO
func (tf *TmysqlParseFile) UploadDdlTblMapFile() (err error) {
	for _, fileName := range tf.Param.FileNames {
		ddlTblFile := fileName + DDLMAP_FILE_SUFFIX
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

// Execute 运行tmysqlpase
//
//	@receiver tf
//	@return err
func (tf *TmysqlParseFile) Execute(resultFile chan string) (err error) {
	var wg sync.WaitGroup
	var errs []error
	c := make(chan struct{}, 10)
	errChan := make(chan error, 5)
	for _, fileName := range tf.Param.FileNames {
		wg.Add(1)
		tf.fileMap[fileName] = fileName + ".json"
		c <- struct{}{}
		go func(sqlfile string) {
			command := exec.Command("/bin/bash", "-c", tf.getCommand(sqlfile))
			logger.Info("command is %s", command)
			output, err := command.CombinedOutput()
			if err != nil {
				errChan <- fmt.Errorf("tmysqlparse.sh command run failed. error info:" + err.Error() + "," + string(output))
			} else {
				resultFile <- sqlfile
			}
			<-c
			wg.Done()
		}(fileName)
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

func (tf *TmysqlParse) getAbsoutputfilePath(inputFileName string) string {
	fileAbPath, _ := filepath.Abs(path.Join(tf.tmpWorkdir, tf.fileMap[inputFileName]))
	return fileAbPath
}

// AnalyzeParseResult TODO
func (t *TmysqlParse) AnalyzeParseResult(resultFile chan string, mysqlVersion string, dbtype string) (err error) {
	var errs []error
	c := make(chan struct{}, 10)
	errChan := make(chan error, 5)
	wg := &sync.WaitGroup{}
	go func() {
		for err := range errChan {
			errs = append(errs, err)
		}
	}()
	for inputFileName := range resultFile {
		wg.Add(1)
		c <- struct{}{}
		go func(fileName string) {
			defer wg.Done()
			err = t.AnalyzeOne(fileName, mysqlVersion, dbtype)
			if err != nil {
				errChan <- err
			}
			<-c
		}(inputFileName)
	}
	wg.Wait()
	close(errChan)
	logger.Info("end to analyze %d files", len(t.fileMap))
	return errors.Join(errs...)
}

// ParseResult TODO
func (c *CheckInfo) ParseResult(rule *RuleItem, res ParseLineQueryBase) {
	matched, err := rule.CheckItem(res.Command)
	if matched {
		if rule.Ban {
			c.BanWarnings = append(c.BanWarnings, RiskInfo{
				Line:        int64(res.QueryId),
				Sqltext:     res.QueryString,
				CommandType: res.Command,
				WarnInfo:    err.Error(),
			})
		} else {
			c.RiskWarnings = append(c.RiskWarnings, RiskInfo{
				Line:        int64(res.QueryId),
				Sqltext:     res.QueryString,
				CommandType: res.Command,
				WarnInfo:    err.Error(),
			})
		}
	}
}

// analyzeDDLTbls TODO
func (tf *TmysqlParse) analyzeDDLTbls(inputfileName string) (err error) {
	ddlTbls := make(map[string][]string)
	defer func() {
		if r := recover(); r != nil {
			logger.Error("panic error:%v,stack:%s", r, string(debug.Stack()))
			logger.Error("Recovered. Error: %v", r)
		}
	}()
	tf.result[inputfileName] = &CheckInfo{}
	f, err := os.Open(tf.getAbsoutputfilePath(inputfileName))
	if err != nil {
		logger.Error("open file failed %s", err.Error())
		return err
	}
	defer f.Close()
	reader := bufio.NewReader(f)
	for {
		line, err_r := reader.ReadBytes(byte('\n'))
		if err_r != nil {
			if err_r == io.EOF {
				break
			}
			logger.Error("read Line Error %s", err_r.Error())
			return err_r
		}
		if len(line) == 1 && line[0] == byte('\n') {
			continue
		}
		var res ParseLineQueryBase
		if err = json.Unmarshal(line, &res); err != nil {
			logger.Error("json unmasrshal line:%s failed %s", string(line), err.Error())
			return err
		}
		// 判断是否有语法错误
		if res.ErrorCode != 0 {
			return err
		}
		switch res.Command {
		case "create_table", "alter_table":
			var o CommDDLResult
			if err = json.Unmarshal(line, &o); err != nil {
				logger.Error("json unmasrshal line failed %s", err.Error())
				return err
			}
			// 如果dbname为空，则实际库名由参数指定,无特殊情况
			ddlTbls[o.DbName] = append(ddlTbls[o.DbName], o.TableName)
		}
	}
	fd, err := os.Create(path.Join(tf.tmpWorkdir, inputfileName+DDLMAP_FILE_SUFFIX))
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

// AnalyzeOne TODO
func (tf *TmysqlParse) AnalyzeOne(inputfileName string, mysqlVersion string, dbtype string) (err error) {
	var idx int
	var syntaxFailInfos []FailedInfo
	var buf []byte
	ddlTbls := make(map[string][]string)
	defer func() {
		if r := recover(); r != nil {
			logger.Error("panic error:%v,stack:%s", r, string(debug.Stack()))
			logger.Error("Recovered. Error: %v", r)
			err = fmt.Errorf("line:%d,err:%v", idx, r)
		}
	}()
	tf.result[inputfileName] = &CheckInfo{}
	f, err := os.Open(tf.getAbsoutputfilePath(inputfileName))
	if err != nil {
		logger.Error("open file failed %s", err.Error())
		return err
	}
	defer f.Close()
	reader := bufio.NewReader(f)
	for {
		idx++
		line, isPrefix, err_r := reader.ReadLine()
		if err_r != nil {
			if err_r == io.EOF {
				break
			}
			logger.Error("read Line Error %s", err_r.Error())
			return err_r
		}
		buf = append(buf, line...)
		if isPrefix {
			continue
		}
		// 清空
		bs := buf
		buf = []byte{}

		var res ParseLineQueryBase
		//	logger.Debug("buf: %s", string(bs))
		if len(bs) == 0 {
			logger.Info("blank line skip")
			continue
		}
		if err = json.Unmarshal(bs, &res); err != nil {
			logger.Error("json unmasrshal line:%s failed %s", string(bs), err.Error())
			return err
		}
		// 判断是否有语法错误
		if res.ErrorCode != 0 {
			syntaxFailInfos = append(syntaxFailInfos, FailedInfo{
				Line:      int64(res.QueryId),
				Sqltext:   res.QueryString,
				ErrorCode: int64(res.ErrorCode),
				ErrorMsg:  res.ErrorMsg,
			})
			continue
		}
		switch dbtype {
		case app.MySQL:
			// tmysqlparse检查结果全部正确，开始判断语句是否符合定义的规则（即虽然语法正确，但语句可能是高危语句或禁用的命令）
			tf.result[inputfileName].ParseResult(R.CommandRule.HighRiskCommandRule, res)
			tf.result[inputfileName].ParseResult(R.CommandRule.BanCommandRule, res)
			tf.result[inputfileName].runcheck(res, bs, mysqlVersion)
		case app.Spider:
			// tmysqlparse检查结果全部正确，开始判断语句是否符合定义的规则（即虽然语法正确，但语句可能是高危语句或禁用的命令）
			tf.result[inputfileName].ParseResult(SR.CommandRule.HighRiskCommandRule, res)
			tf.result[inputfileName].ParseResult(SR.CommandRule.BanCommandRule, res)
			tf.result[inputfileName].runSpidercheck(ddlTbls, res, bs, mysqlVersion)
		}
	}
	// if dbtype == app.Spider {
	// 	fd, err := os.Create(path.Join(tf.tmpWorkdir, inputfileName+DDLMAP_FILE_SUFFIX))
	// 	if err != nil {
	// 		logger.Error("create file failed %s", err.Error())
	// 		return err
	// 	}
	// 	defer fd.Close()
	// 	b, err := json.Marshal(ddlTbls)
	// 	if err != nil {
	// 		logger.Error("json marshal failed %s", err.Error())
	// 		return err
	// 	}
	// 	_, err = fd.Write(b)
	// 	if err != nil {
	// 		logger.Error("write file failed %s", err.Error())
	// 		return err
	// 	}
	// }
	tf.result[inputfileName].SyntaxFailInfos = syntaxFailInfos
	return nil
}

func (ch *CheckInfo) runSpidercheck(ddlTbls map[string][]string, res ParseLineQueryBase, bs []byte,
	mysqlVersion string) (err error) {
	var c SpiderChecker
	// 其他规则分析
	switch res.Command {
	case "create_table":
		var o CreateTableResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmasrshal line failed %s", err.Error())
			return err
		}
		o.TableOptionMap = ConverTableOptionToMap(o.TableOptions)
		c = o
		// 如果dbname为空，则实际库名由参数指定,无特殊情况
		ddlTbls[o.DbName] = append(ddlTbls[o.DbName], o.TableName)
	case "create_db":
		var o CreateDBResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmasrshal line failed %s", err.Error())
			return err
		}
		c = o
	case "alter_table":
		var o AlterTableResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmasrshal line failed %s", err.Error())
			return err
		}
		ddlTbls[o.DbName] = append(ddlTbls[o.DbName], o.TableName)
	}
	if c == nil {
		return nil
	}
	// 不同结构体绑定不同的Checker
	result := c.SpiderChecker(mysqlVersion)
	if result.IsPass() {
		return nil
	}
	if len(result.BanWarns) > 0 {
		ch.BanWarnings = append(ch.BanWarnings, RiskInfo{
			Line:        int64(res.QueryId),
			Sqltext:     res.QueryString,
			CommandType: res.Command,
			WarnInfo:    prettyErrorsOutput(result.BanWarns),
		})
	}
	if len(result.RiskWarns) > 0 {
		ch.RiskWarnings = append(ch.RiskWarnings, RiskInfo{
			Line:        int64(res.QueryId),
			Sqltext:     res.QueryString,
			CommandType: res.Command,
			WarnInfo:    prettyErrorsOutput(result.RiskWarns),
		})
	}
	return err
}

func (ch *CheckInfo) runcheck(res ParseLineQueryBase, bs []byte, mysqlVersion string) (err error) {
	var c Checker
	// 其他规则分析
	switch res.Command {
	case "create_table":
		var o CreateTableResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmasrshal line failed %s", err.Error())
			return err
		}
		c = o
	case "alter_table":
		var o AlterTableResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmasrshal line failed %s", err.Error())
			return err
		}
		c = o
	case "delete":
		var o DeleteResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmasrshal line failed %s", err.Error())
			return err
		}
		c = o
	case "update":
		var o UpdateResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmasrshal line failed %s", err.Error())
			return err
		}
		c = o
	case "create_function", "create_trigger", "create_event", "create_procedure", "create_view":
		var o DefinerBase
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmasrshal line failed %s", err.Error())
			return err
		}
		c = o
	case "create_db":
		var o CreateDBResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmasrshal line failed %s", err.Error())
			return err
		}
		c = o
	}

	if c == nil {
		return nil
	}
	// 不同结构体绑定不同的Checker
	result := c.Checker(mysqlVersion)
	if result.IsPass() {
		return nil
	}
	if len(result.BanWarns) > 0 {
		ch.BanWarnings = append(ch.BanWarnings, RiskInfo{
			Line:        int64(res.QueryId),
			Sqltext:     res.QueryString,
			CommandType: res.Command,
			WarnInfo:    prettyErrorsOutput(result.BanWarns),
		})
	}
	if len(result.RiskWarns) > 0 {
		ch.RiskWarnings = append(ch.RiskWarnings, RiskInfo{
			Line:        int64(res.QueryId),
			Sqltext:     res.QueryString,
			CommandType: res.Command,
			WarnInfo:    prettyErrorsOutput(result.RiskWarns),
		})
	}
	return err
}

func prettyErrorsOutput(warnInfos []string) (msg string) {
	for idx, v := range warnInfos {
		msg += fmt.Sprintf("Error %d: %s\n", idx+1, v)
	}
	return
}
