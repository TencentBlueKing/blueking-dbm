package dbareport

import (
	"path/filepath"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/reportlog"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// ReportLogger TODO
type ReportLogger struct {
	Result reportlog.Reporter
	Files  reportlog.Reporter
	Status reportlog.Reporter
}

// reportLogger 全局可调用的 log reporter
var reportLogger *ReportLogger

// InitReporter TODO
func InitReporter(reportDir string) (err error) {
	reportLogger, err = NewLogReporter(reportDir)
	return err
}

// Report 返回reportLogger
func Report() *ReportLogger {
	return reportLogger
}

// NewLogReporter TODO
func NewLogReporter(reportDir string) (*ReportLogger, error) {
	logOpt := reportlog.LoggerOption{
		MaxSize:    5,
		MaxBackups: 30,
		MaxAge:     60,
	}
	resultReport, err := reportlog.NewReporter(reportDir, "backup_result.log", &logOpt)
	if err != nil {
		logger.Log.Warn("fail to init resultReporter:%s", err.Error())
		//resultReport.Disable = true
		return nil, errors.WithMessage(err, "fail to init resultReporter")
	}
	filesReport, err := reportlog.NewReporter(filepath.Join(reportDir, "result"), "dbareport_result.log", &logOpt)
	if err != nil {
		logger.Log.Warn("fail to init statusReporter:%s", err.Error())
		//filesReport.Disable = true
		return nil, errors.WithMessage(err, "fail to init statusReporter")
	}
	statusReport, err := reportlog.NewReporter(filepath.Join(reportDir, "status"), "backup_status.log", &logOpt)
	if err != nil {
		logger.Log.Warn("fail to init statusReporter:%s", err.Error())
		//statusReport.Disable = true
		return nil, errors.WithMessage(err, "fail to init statusReporter")
	}
	return &ReportLogger{
		Result: *resultReport,
		Files:  *filesReport,
		Status: *statusReport,
	}, nil
}
