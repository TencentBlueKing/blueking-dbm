package reportlog

import (
	"encoding/json"
	"log"
	"os"
	"path/filepath"

	"dbm-services/common/go-pubpkg/cmutil"

	"github.com/pkg/errors"
	"gopkg.in/natefinch/lumberjack.v2"
)

// Reporter TODO
type Reporter struct {
	ReportPath string `json:"report_path"`
	Filename   string `json:"filename"`
	LogOpt     *LoggerOption
	Disable    bool
	log        *log.Logger
}

// LoggerOption TODO
type LoggerOption struct {
	MaxSize    int
	MaxBackups int
	MaxAge     int
	Compress   bool
}

func defaultLoggerOpt() *LoggerOption {
	return &LoggerOption{
		MaxSize:    100, // MB
		MaxBackups: 10,  // num
		MaxAge:     30,  // days
		// report Compress 建议开启 compress，因为 lumberjack 默认 rotate 文件名格式是 report-2025-01-09T08-18-41.933.log
		//  日志采集如果没配置好可能会重复采集 *.log
		Compress: true,
	}
}

// NewReporter init reporter for logFile path
// reportDir maybe like '/home/mysql/dbareport/mysql/dbbackup'
func NewReporter(reportDir, filename string, logOpt *LoggerOption) (*Reporter, error) {
	logFilePath := filepath.Join(reportDir, filename)
	var reporter *Reporter = &Reporter{
		log: &log.Logger{},
	}

	if reportDir == "" {
		return nil, errors.Errorf("invalid reportDir:%s", reportDir)
	} else if link, _ := cmutil.IsSymLinkFile(reportDir); link {
		_ = os.Remove(reportDir) // /home/mysql/dbareport 不使用软连
	}
	if !cmutil.IsDirectory(reportDir) {
		if err := os.MkdirAll(reportDir, 0755); err != nil {
			return nil, errors.Wrap(err, "create report path")
		}
	}
	if !cmutil.FileExists(logFilePath) {
		// lumberjack 默认创建的文件权限是 600
		if f, err := os.OpenFile(logFilePath, os.O_CREATE|os.O_WRONLY, 0644); err != nil {
			return nil, err
		} else {
			f.Close()
		}
	}

	if logOpt == nil {
		logOpt = defaultLoggerOpt()
	}

	resultLogger := &lumberjack.Logger{
		Filename:   logFilePath,
		MaxSize:    logOpt.MaxSize,
		MaxBackups: logOpt.MaxBackups,
		MaxAge:     logOpt.MaxAge,
		Compress:   logOpt.Compress,
		LocalTime:  true,
	}
	reporter.log.SetOutput(resultLogger)
	return reporter, nil
}

// Print TODO
func (r *Reporter) Print(v interface{}) {
	bs, _ := json.Marshal(v)
	if !r.Disable {
		r.log.Println(string(bs))
	}
}

// Println TODO
func (r *Reporter) Println(v interface{}) {
	bs, _ := json.Marshal(v)
	if !r.Disable {
		r.log.Println(string(bs))
	}
}
