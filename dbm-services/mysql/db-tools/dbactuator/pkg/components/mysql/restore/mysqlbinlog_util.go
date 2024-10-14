package restore

import (
	"fmt"
	"path/filepath"
	"strings"
	"time"

	"github.com/pkg/errors"
	"github.com/spf13/cast"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// MySQLBinlogUtil TODO

// MySQLBinlogUtil TODO
type MySQLBinlogUtil struct {
	// --start-datetime  时间格式
	// 格式 "2006-01-02 15:04:05" 原样传递给 mysqlbinlog
	// 格式"2006-01-02T15:04:05Z07:00"(示例"2023-12-11T05:03:05+08:00")按照机器本地时间，解析成 "2006-01-02 15:04:05" 再传递给 mysqlbinlog
	// 在 Init 时会统一把时间字符串转换成 time.RFC3399
	StartTime string `json:"start_time"`
	// --stop-datetime   时间格式同 StartTime，可带时区，会转换成机器本地时间
	StopTime string `json:"stop_time"`
	// --start-position
	StartPos uint `json:"start_pos,omitempty"`
	// --stop-position
	StopPos uint `json:"stop_pos,omitempty"`
	// 是否开启幂等模式, mysqlbinlog --idempotent(>=5.7)
	IdempotentMode bool `json:"idempotent_mode"`
	// 导入时是否记录 binlog, mysql sql_log_bin=0 or mysqlbinlog --disable-log-bin. true表示不写
	NotWriteBinlog bool `json:"not_write_binlog"`

	// row event 解析指定 databases。必须是精确，不能是通配
	Databases []string `json:"databases,omitempty"`
	// row event 解析指定 tables。必须是精确，不能是通配
	Tables []string `json:"tables,omitempty"`
	// row event 解析指定 忽略 databases
	DatabasesIgnore []string `json:"databases_ignore,omitempty"`
	// row event 解析指定 忽略 tables
	TablesIgnore []string `json:"tables_ignore,omitempty"`

	// query event 默认处理策略。keep:保留解析出的query event 语句, ignore:注释(丢弃)该 query event, error:认为是不接受的语句，报错
	// 默认 keep
	QueryEventHandler string `json:"query_event_handler" enums:"keep,ignore,safe,error"`
	// 匹配字符串成功，强制忽略语句，加入注释中。当与 filter_statement_match_error 都匹配时，ignore_force会优先生效
	// 默认 infodba_schema
	FilterStatementMatchIgnoreForce string `json:"filter_statement_match_ignore_force"`
	// 匹配字符串成功，则解析 binlog 报错
	FilterStatementMatchError string `json:"filter_statement_match_error"`
	// 匹配字符串成功，则忽略语句，加入注释中
	FilterStatementMatchIgnore string `json:"filter_statement_match_ignore"`

	// --rewrite_db="db1->xx_db1,db2->xx_db2"
	RewriteDB string `json:"rewrite_db"`

	MySQLClientOpt *MySQLClientOpt `json:"mysql_client_opt"`
	// 是否启用 flashback
	Flashback bool `json:"flashback,omitempty"`

	// mysqlbinlog options string
	options   string
	cmdArgs   []string
	workDir   string
	binlogCmd string
}

func (b *MySQLBinlogUtil) BuildArgs() ([]string, error) {
	b.cmdArgs = nil
	if b.StartPos == 0 && b.StartTime == "" {
		return nil, errors.Errorf("start_datetime and start_pos cannot be empty both")
	}
	// 优先使用 start_pos
	if b.StartPos > 0 {
		b.cmdArgs = append(b.cmdArgs, "--start-position", cast.ToString(b.StartPos))
	}
	if b.StartTime != "" {
		_, err := time.ParseInLocation(time.DateTime, b.StartTime, time.Local)
		if err != nil {
			return nil, errors.Errorf("start_time expect format %s but got %s", time.DateTime, b.StartTime)
		}
		b.cmdArgs = append(b.cmdArgs, "--start-datetime", b.StartTime)
	}
	if b.StopTime != "" {
		_, err := time.ParseInLocation(time.DateTime, b.StopTime, time.Local)
		if err != nil {
			return nil, errors.Errorf("stop_time expect format %s but got %s", time.DateTime, b.StopTime)
		}
		b.cmdArgs = append(b.cmdArgs, "--stop-datetime=", b.StopTime)
	} else {
		return nil, errors.Errorf("stop_datetime cannot be empty")
	}

	b.cmdArgs = append(b.cmdArgs, "--base64-output=auto")
	if b.NotWriteBinlog {
		b.cmdArgs = append(b.cmdArgs, "--disable-log-bin")
	}
	if b.IdempotentMode && mysqlbinlogHasOpt(b.binlogCmd, "--idempotent") == nil {
		b.cmdArgs = append(b.cmdArgs, "--idempotent")
	}

	filterOpts := ""
	if b.Flashback {
		filterOpts += " --flashback"
	}
	if len(b.Databases) > 0 {
		filterOpts += fmt.Sprintf(" --databases='%s'", strings.Join(b.Databases, ","))
	}
	if len(b.Tables) > 0 {
		filterOpts += fmt.Sprintf(" --tables='%s'", strings.Join(b.Tables, ","))
	}
	if len(b.DatabasesIgnore) > 0 {
		filterOpts += fmt.Sprintf(" --databases-ignore='%s'", strings.Join(b.DatabasesIgnore, ","))
	}
	if len(b.TablesIgnore) > 0 {
		filterOpts += fmt.Sprintf(" --tables-ignore='%s'", strings.Join(b.TablesIgnore, ","))
	}
	if filterOpts == "" {
		logger.Warn("quick_mode=true shall works with binlog-filter data import")
	}
	if filterOpts == "" && !b.IdempotentMode {
		return nil, errors.Errorf("no binlog-filter need idempotent_mode=true")
	}
	// query event 都全部应用，没法做部分过滤。前提是表结构已全部导入，否则导入会报错。也可以设置为 error 模式，解析时就会报错
	if b.QueryEventHandler == "" {
		b.QueryEventHandler = "keep"
	}
	filterOpts += fmt.Sprintf(" --query-event-handler=%s", b.QueryEventHandler)
	// 正向解析，不设置 --filter-statement-match-error
	if b.Flashback {
		if len(b.Tables) > 0 {
			filterOpts += fmt.Sprintf(" --filter-statement-match-error=\"%s\"", strings.Join(b.Tables, ","))
		} else {
			filterOpts += fmt.Sprintf(" --filter-statement-match-error=\"%s\"", strings.Join(b.Databases, ","))
		}
		filterOpts += fmt.Sprintf(" --filter-statement-match-ignore=\"flush ,FLUSH ,create table,CREATE TABLE\"")
	}
	filterOpts += fmt.Sprintf(" --filter-statement-match-ignore-force=\"%s\"", native.INFODBA_SCHEMA)
	b.cmdArgs = append(b.cmdArgs, filterOpts)
	return nil, nil
}

func (b *MySQLBinlogUtil) Parse(binlogDir string, fileName string) (string, error) {
	_, err := b.BuildArgs()
	if err != nil {
		return "", err
	}
	parsedFileName := fmt.Sprintf(`%s/%s.sql`, dirBinlogParsed, fileName)
	binlogFile := filepath.Join(binlogDir, fileName)
	cmdArgs := strings.Join(b.cmdArgs, " ")
	cmdStr := ""
	if b.workDir != "" {
		cmdStr += fmt.Sprintf("cd %s && ", b.workDir)
	}
	cmdStr += fmt.Sprintf("%s %s %s >%s", b.binlogCmd, cmdArgs, binlogFile, parsedFileName)
	//logger.Info("run: %s", cmd)
	if outStr, err := osutil.ExecShellCommand(false, cmdStr); err != nil {
		return parsedFileName, errors.Wrapf(err, "fail to parse %s: %s, cmd: %s", fileName, outStr, cmdStr)
	}
	return parsedFileName, nil
}

func (b *MySQLBinlogUtil) ReturnParseCommand(binlogDir string, fileNames []string) string {
	binlogFiles := strings.Join(fileNames, ",")
	cmdArgs := strings.Join(b.cmdArgs, " ")
	cmd := fmt.Sprintf("cd %s && %s %s %s ", binlogDir, b.binlogCmd, cmdArgs, binlogFiles)
	return cmd
}

func (b *MySQLBinlogUtil) SetCmdPath(cmdPath string) {
	b.binlogCmd = cmdPath
}
func (b *MySQLBinlogUtil) SetWorkDir(workDir string) {
	b.workDir = workDir
}

// mysqlbinlogHasOpt return nil if option exists
func mysqlbinlogHasOpt(binlogCmd string, option string) error {
	outStr, errStr, err := cmutil.ExecCommand(false, "", binlogCmd, "--help")
	if err != nil {
		return err
	}
	if strings.Contains(errStr, option) || strings.Contains(outStr, option) {
		return nil
	} else {
		return errors.Errorf("mysqlbinlog %s has no option %s", binlogCmd, option)
	}
}
