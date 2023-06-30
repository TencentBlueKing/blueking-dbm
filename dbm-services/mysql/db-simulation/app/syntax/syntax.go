// Package syntax TODO
package syntax

import (
	"bufio"
	"encoding/json"
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
	"strings"
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
	Param CheckSqlFileParam
}

// CheckSqlFileParam TODO
type CheckSqlFileParam struct {
	BkRepoBasePath string   `json:"bkrepo_base_path"` // 制品库相对路径
	FileNames      []string `json:"file_names"`       // SQL文件名称
	MysqlVersion   string   `json:"mysql_version"`    // mysql版本
}

// TmysqlParse TODO
type TmysqlParse struct {
	TmysqlParseBinPath string
	BaseWorkdir        string
	result             map[string]*CheckInfo
	runtimeCtx
	bkRepoClient *bkrepo.BkRepoClient
}

type runtimeCtx struct {
	tmpWorkdir string
	fileMap    map[inputFileName]outputFileName
}

// CheckInfo TODO
type CheckInfo struct {
	SyntaxFailInfos []FailedInfo `json:"syntax_fails"`
	RiskWarnings    []RiskInfo   `json:"highrisk_warnings"`
	BanWarnings     []RiskInfo   `json:"bancommand_warnings"`
}

// FailedInfo TODO
type FailedInfo struct {
	Line      int64  `json:"line"`
	Sqltext   string `json:"sqltext"`
	ErrorCode int64  `json:"error_code"`
	ErrorMsg  string `json:"error_msg"`
}

// RiskInfo TODO
type RiskInfo struct {
	Line        int64  `json:"line"`
	CommandType string `json:"command_type"`
	Sqltext     string `json:"sqltext"`
	WarnInfo    string `json:"warn_info"`
}

var lock sync.Mutex

// DoSQL TODO
func (tf *TmysqlParseFile) DoSQL(dbtype string) (result map[string]*CheckInfo, err error) {
	tf.fileMap = make(map[inputFileName]outputFileName)
	tf.result = make(map[string]*CheckInfo)
	tf.tmpWorkdir = tf.BaseWorkdir
	if err = tf.Execute(); err != nil {
		logger.Error("failed to execute tmysqlparse: %s", err.Error())
		return nil, err
	}
	logger.Info("err is %v", err)
	// 对tmysqlparse的处理结果进行分析，为json文件，后面用到了rule
	mysqlVersion := tf.Param.MysqlVersion
	if err = tf.AnalyzeParseResult(mysqlVersion, dbtype); err != nil {
		logger.Error("failed to analyze the parsing result:%s", err.Error())
		return tf.result, err
	}

	return tf.result, nil
}

// Do  运行语法检查 For SQL 文件
//
//	@receiver tf
//	@return result
//	@return err
func (tf *TmysqlParseFile) Do(dbtype string) (result map[string]*CheckInfo, err error) {
	logger.Info("doing....")
	if err = tf.Init(); err != nil {
		logger.Error("Do init failed %s", err.Error())
		return nil, err
	}
	// 最后删除临时目录,不会返回错误
	// 暂时屏蔽 观察过程文件
	defer tf.delTempDir()

	if err = tf.Downloadfile(); err != nil {
		logger.Error("failed to download sql file from the product library %s", err.Error())
		return nil, err
	}

	if err = tf.Execute(); err != nil {
		logger.Error("failed to execute tmysqlparse: %s", err.Error())
		return nil, err
	}
	logger.Info("err is %v", err)
	// 对tmysqlparse的处理结果进行分析，为json文件，后面用到了rule
	mysqlVersion := tf.Param.MysqlVersion
	if err = tf.AnalyzeParseResult(mysqlVersion, dbtype); err != nil {
		logger.Error("failed to analyze the parsing result:%s", err.Error())
		return tf.result, err
	}

	return tf.result, nil
}

// Init TODO
func (t *TmysqlParse) Init() (err error) {
	tmpDir := fmt.Sprintf("tmysqlparse_%s_%s", time.Now().Format("20060102150405"), strconv.Itoa(rand.Intn(10000)))
	t.tmpWorkdir = path.Join(t.BaseWorkdir, tmpDir)
	if err = os.MkdirAll(t.tmpWorkdir, os.ModePerm); err != nil {
		logger.Error("mkdir %s failed, err:%+v", t.tmpWorkdir, err)
		return fmt.Errorf("failed to initialize tmysqlparse temporary directory(%s).detail:%s", t.tmpWorkdir, err.Error())
	}
	t.bkRepoClient = &bkrepo.BkRepoClient{
		Client: &http.Client{
			Transport: &http.Transport{},
		},
		BkRepoProject:   config.GAppConfig.BkRepo.Project,
		BkRepoPubBucket: config.GAppConfig.BkRepo.PublicBucket,
		BkRepoUser:      config.GAppConfig.BkRepo.User,
		BkRepoPwd:       config.GAppConfig.BkRepo.Pwd,
		BkRepoEndpoint:  config.GAppConfig.BkRepo.EndPointUrl,
	}
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
	for _, fileName := range tf.Param.FileNames {
		err = tf.bkRepoClient.Download(tf.Param.BkRepoBasePath, fileName, tf.tmpWorkdir)
		if err != nil {
			logger.Error("download %s from bkrepo failed :%s", fileName, err.Error())
			return err
		}
	}
	return
}

// Execute 运行tmysqlpase
//
//	@receiver tf
//	@return err
func (tf *TmysqlParseFile) Execute() (err error) {
	var wg sync.WaitGroup
	var mu sync.Mutex
	var errs []string
	c := make(chan struct{}, 10)
	for _, fileName := range tf.Param.FileNames {
		wg.Add(1)
		tf.fileMap[fileName] = fileName + ".json"
		c <- struct{}{}
		go func() {
			command := exec.Command("/bin/bash", "-c", tf.getCommand(fileName))
			logger.Info("command is %s", command)
			output, err := command.CombinedOutput()
			if err != nil {
				mu.Lock()
				errs = append(errs, fmt.Sprintf("tmysqlparse.sh command run failed. error info:"+err.Error()+","+string(output)))
				mu.Unlock()
			}
			<-c
			wg.Done()
		}()
		wg.Wait()
	}
	if len(errs) > 0 {
		return fmt.Errorf("errrors: %s", strings.Join(errs, "\n"))
	}
	return err
}

func (tf *TmysqlParse) getAbsoutputfilePath(inputFileName string) string {
	fileAbPath, _ := filepath.Abs(path.Join(tf.tmpWorkdir, tf.fileMap[inputFileName]))
	return fileAbPath
}

// AnalyzeParseResult TODO
func (t *TmysqlParse) AnalyzeParseResult(mysqlVersion string, dbtype string) (err error) {
	wg := &sync.WaitGroup{}
	var errs []string
	c := make(chan struct{}, 10)
	// 开启多个线程，同时对多个sql文件进行分析
	for inputFileName := range t.fileMap {
		wg.Add(1)
		c <- struct{}{}
		go func(fileName string) {
			err = t.AnalyzeOne(fileName, mysqlVersion, dbtype)
			if err != nil {
				errs = append(errs, err.Error())
			}
			<-c
			wg.Done()
		}(inputFileName)
	}
	wg.Wait()
	if len(errs) > 0 {
		return fmt.Errorf("errors: %s", strings.Join(errs, "\n"))
	}
	return err
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

// AnalyzeOne TODO
func (tf *TmysqlParse) AnalyzeOne(inputfileName string, mysqlVersion string, dbtype string) (err error) {
	var idx int
	defer func() {
		if r := recover(); r != nil {
			logger.Error("panic error:%v,stack:%s", r, string(debug.Stack()))
			logger.Error("Recovered. Error: %v", r)
			err = fmt.Errorf("line:%d,err:%v", idx, r)
		}
	}()
	lock.Lock()
	tf.result[inputfileName] = &CheckInfo{}
	f, err := os.Open(tf.getAbsoutputfilePath(inputfileName))
	if err != nil {
		logger.Error("open file failed %s", err.Error())
		return
	}
	defer f.Close()
	reader := bufio.NewReader(f)
	var syntaxFailInfos []FailedInfo
	var buf []byte
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
		logger.Debug("buf: %s", string(bs))
		if len(bs) == 0 {
			logger.Info("blank line skip")
			continue
		}
		if err = json.Unmarshal(bs, &res); err != nil {
			logger.Error("json unmasrshal line:%s failed %s", string(bs), err.Error())
			return
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
			//
			tf.result[inputfileName].runcheck(res, bs, mysqlVersion)
		case app.Spider:
			// tmysqlparse检查结果全部正确，开始判断语句是否符合定义的规则（即虽然语法正确，但语句可能是高危语句或禁用的命令）
			tf.result[inputfileName].ParseResult(SR.CommandRule.HighRiskCommandRule, res)
			tf.result[inputfileName].ParseResult(SR.CommandRule.BanCommandRule, res)
			tf.result[inputfileName].runSpidercheck(res, bs, mysqlVersion)
		}
	}
	tf.result[inputfileName].SyntaxFailInfos = syntaxFailInfos
	lock.Unlock()
	return nil
}

func (ch *CheckInfo) runSpidercheck(res ParseLineQueryBase, bs []byte, mysqlVersion string) (err error) {
	var c SpiderChecker
	// 其他规则分析
	switch res.Command {
	case "create_table":
		var o CreateTableResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmasrshal line failed %s", err.Error())
			return
		}
		o.TableOptionMap = ConverTableOptionToMap(o.TableOptions)
		c = o
	case "create_db":
		var o CreateDBResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmasrshal line failed %s", err.Error())
			return
		}
		c = o
	}
	if c == nil {
		return
	}
	// 不同结构体绑定不同的Checker
	result := c.SpiderChecker(mysqlVersion)
	if result.IsPass() {
		return
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
			return
		}
		c = o
	case "alter_table":
		var o AlterTableResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmasrshal line failed %s", err.Error())
			return
		}
		c = o
	case "delete":
		var o DeleteResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmasrshal line failed %s", err.Error())
			return
		}
		c = o
	case "update":
		var o UpdateResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmasrshal line failed %s", err.Error())
			return
		}
		c = o
	case "create_function", "create_trigger", "create_event", "create_procedure", "create_view":
		var o DefinerBase
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmasrshal line failed %s", err.Error())
			return
		}
		logger.Info("detail %v", o.Definer)
		c = o
	case "create_db":
		var o CreateDBResult
		if err = json.Unmarshal(bs, &o); err != nil {
			logger.Error("json unmasrshal line failed %s", err.Error())
			return
		}
		c = o
	}

	if c == nil {
		return
	}
	// 不同结构体绑定不同的Checker
	result := c.Checker(mysqlVersion)
	if result.IsPass() {
		return
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
