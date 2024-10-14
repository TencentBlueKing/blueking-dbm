package restore

import (
	"fmt"
	"path/filepath"
	"strings"
	"time"

	"github.com/pkg/errors"
	"github.com/spf13/cast"

	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// BinlogUtil 解析一个 binlog
type BinlogUtil interface {
	BuildArgs(filterMode bool) ([]string, error)
	Parse(binlogDir, fileName string, filterMode bool) (string, error)
}

// GoMySQLBinlogUtil TODO
type GoMySQLBinlogUtil struct {
	// File one binlog file name
	File      string `json:"-"`
	BinlogDir string `json:"-"`
	StartFile string `json:"-"`
	StopFile  string `json:"-"`
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
	Idempotent bool `json:"idempotent"`
	Autocommit bool `json:"autocommit"`
	// 导入时是否记录 binlog, mysql sql_log_bin=0 or mysqlbinlog --disable-log-bin. true表示不写
	DisableLogBin         bool `json:"disable_log_bin"`
	ConvRowsUpdateToWrite bool `json:"conv_rows_update_to_write"`
	// --rewrite-db="db1->xx_db1,db2->xx_db2"
	RewriteDB []string `json:"rewrite_db"`

	RowsEventType string `json:"rows_event_type"`
	RowsFilter    string `json:"rows_filter"`
	// row event 解析指定 databases。必须是精确，不能是通配
	Databases []string `json:"databases,omitempty"`
	// row event 解析指定 tables。必须是精确，不能是通配
	Tables []string `json:"tables,omitempty"`
	// row event 解析指定 忽略 databases
	ExcludeDatabases []string `json:"exclude_databases,omitempty"`
	// row event 解析指定 忽略 tables
	ExcludeTables []string `json:"exclude_tables,omitempty"`

	Verbose int `json:"-"`
	//MySQLClientOpt *MySQLClientOpt `json:"mysql_client_opt"`
	// 是否启用 flashback
	Flashback bool `json:"flashback,omitempty"`

	workDir string
	cmdArgs []string
	cmdPath string
}

// BuildArgs 每次 Parse 之前都要调用BuildArgs，因为 StartPos,StopPos 是跟 binlog 文件关联的
func (b *GoMySQLBinlogUtil) BuildArgs(filterMode bool) ([]string, error) {
	b.cmdArgs = nil
	if b.Flashback {
		b.cmdArgs = append(b.cmdArgs, "--flashback")
	}
	if b.Idempotent {
		b.cmdArgs = append(b.cmdArgs, "--idempotent")
	}
	if b.Autocommit {
		b.cmdArgs = append(b.cmdArgs, "--autocommit")
	}
	if b.ConvRowsUpdateToWrite {
		b.cmdArgs = append(b.cmdArgs, "--conv-rows-update-to-write")
	}
	if b.DisableLogBin {
		b.cmdArgs = append(b.cmdArgs, "--disable-log-bin")
	}
	if b.RowsEventType != "" {
		b.cmdArgs = append(b.cmdArgs, "--rows-event-type", b.RowsEventType)
	}
	if filterMode {
		if b.RowsFilter != "" {
			//b.cmdArgs = append(b.cmdArgs, "--rows-filter", b.RowsFilter)
			b.cmdArgs = append(b.cmdArgs, fmt.Sprintf("--rows-filter='%s'", b.RowsFilter))
		}
		if len(b.Databases) > 0 {
			b.cmdArgs = append(b.cmdArgs, "--databases", strings.Join(b.Databases, ","))
		}
		if len(b.Tables) > 0 {
			b.cmdArgs = append(b.cmdArgs, "--tables", strings.Join(b.Tables, ","))
		}
		if len(b.ExcludeDatabases) > 0 {
			b.cmdArgs = append(b.cmdArgs, "--databases", strings.Join(b.Databases, ","))
		}
		if len(b.ExcludeTables) > 0 {
			b.cmdArgs = append(b.cmdArgs, "--exclude-tables", strings.Join(b.ExcludeTables, ","))
		}
	}

	if len(b.RewriteDB) > 0 {
		for _, rule := range b.RewriteDB {
			b.cmdArgs = append(b.cmdArgs, "--rewrite-db", rule)
		}
	}
	if b.StartTime != "" {
		_, err := time.ParseInLocation(time.DateTime, b.StartTime, time.Local)
		if err != nil {
			return nil, errors.Errorf("start_time expect format %s but got %s", time.DateTime, b.StartTime)
		}
		b.cmdArgs = append(b.cmdArgs, fmt.Sprintf("--start-datetime='%s'", b.StartTime))
	}
	if b.StopTime != "" {
		_, err := time.ParseInLocation(time.DateTime, b.StopTime, time.Local)
		if err != nil {
			return nil, errors.Errorf("stop_time expect format %s but got %s", time.DateTime, b.StopTime)
		}
		b.cmdArgs = append(b.cmdArgs, fmt.Sprintf("--stop-datetime='%s'", b.StopTime))
	} else {
		return nil, errors.Errorf("stop-datetime cannot be empty")
	}
	if b.StartPos > 0 {
		b.cmdArgs = append(b.cmdArgs, "--start-position", cast.ToString(b.StartPos))
	}
	if b.StopPos > 0 {
		b.cmdArgs = append(b.cmdArgs, "--stop-position", cast.ToString(b.StopPos))
	}
	//b.cmdArgs = append(b.cmdArgs, "--file", b.File)
	return b.cmdArgs, nil
}

func (b *GoMySQLBinlogUtil) Parse(binlogDir, fileName string, filterMode bool) (string, error) {
	_, err := b.BuildArgs(filterMode)
	if err != nil {
		return "", err
	}
	parsedFile := fmt.Sprintf(`%s/%s.sql`, dirBinlogParsed, fileName)
	binlogFile := filepath.Join(binlogDir, fileName)
	cmdStr := ""
	if b.workDir != "" {
		cmdStr += fmt.Sprintf("cd %s && ", b.workDir)
	}
	cmdStr += fmt.Sprintf("%s %s --file %s  -r %s",
		b.cmdPath, strings.Join(b.cmdArgs, " "), binlogFile, parsedFile)
	if outStr, err := osutil.ExecShellCommand(false, cmdStr); err != nil {
		return parsedFile, errors.Wrapf(err, "fail to parse %s: %s, cmd: %s", fileName, outStr, cmdStr)
	}
	return parsedFile, nil
}

func (b *GoMySQLBinlogUtil) ReturnParseCommand(binlogDir string, fileNames []string) string {
	binlogFiles := strings.Join(fileNames, ",")
	cmd := fmt.Sprintf("cd %s && %s %s -f %s ", binlogDir, b.cmdPath, strings.Join(b.cmdArgs, ","), binlogFiles)
	return cmd
}

func (b *GoMySQLBinlogUtil) SetCmdPath(cmdPath string) {
	b.cmdPath = cmdPath
}
func (b *GoMySQLBinlogUtil) SetWorkDir(workDir string) {
	b.workDir = workDir
}

func (b *GoMySQLBinlogUtil) Check() error {
	return nil
}

func NewGoMySQLBinlogUtil(cmdPath string) *GoMySQLBinlogUtil {
	tool := &GoMySQLBinlogUtil{
		cmdPath: cmdPath,
	}
	return tool
}
