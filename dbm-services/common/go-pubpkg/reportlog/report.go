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
		MaxSize:    5,  // MB
		MaxBackups: 10, // num
		MaxAge:     30, // days
		Compress:   false,
	}
}

// Println TODO
func (r *Reporter) Println(v interface{}) {
	bs, _ := json.Marshal(v)
	r.log.Println(string(bs))
}

// NewReporter init reporter for logFile path
func NewReporter(reportDir, filename string, logOpt *LoggerOption) (*Reporter, error) {
	logFilePath := filepath.Join(reportDir, filename)
	var reporter *Reporter = &Reporter{
		log: &log.Logger{},
	}
	if reportDir == "" {
		return nil, errors.Errorf("invalid reportDir:%s", reportDir)
	} else if !cmutil.IsDirectory(reportDir) {
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
	/*
		statusFile := "binlog_status.log"
		statusLogger := &lumberjack.Logger{
			Filename:   filepath.Join(viper.GetString("report.filepath"), statusFile),
			MaxSize:    5, // MB
			MaxBackups: 10,
			MaxAge:     30,   // days
			Compress:   true, // disabled by default
		}
		statusReporter := new(log.Logger)
		statusReporter.SetOutput(statusLogger)
		reporter.Status = &logPrint{log: statusReporter}
	*/
	if logOpt == nil {
		logOpt = defaultLoggerOpt()
	}

	resultLogger := &lumberjack.Logger{
		Filename:   logFilePath,
		MaxSize:    logOpt.MaxSize,
		MaxBackups: logOpt.MaxBackups,
		MaxAge:     logOpt.MaxAge,
		Compress:   logOpt.Compress,
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
