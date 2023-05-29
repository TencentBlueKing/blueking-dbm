package log

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/reportlog"

	"github.com/pkg/errors"
	"github.com/spf13/viper"
)

// RotateReporters TODO
type RotateReporters struct {
	Result reportlog.Reporter
	Status reportlog.Reporter
}

var reporter *RotateReporters

// InitReporter TODO
func InitReporter() (err error) {
	reporter, err = NewRotateReporter()
	return err
}

// Reporter TODO
func Reporter() *RotateReporters {
	return reporter
}

// NewRotateReporter TODO
func NewRotateReporter() (*RotateReporters, error) {
	reportDir := viper.GetString("report.filepath")
	logOpt := reportlog.LoggerOption{
		MaxSize:    viper.GetInt("report.log_maxsize"), // MB
		MaxBackups: viper.GetInt("report.log_maxbackups"),
		MaxAge:     viper.GetInt("report.log_maxage"),
	}
	resultReport, err := reportlog.NewReporter(reportDir, "binlog_result.log", &logOpt)
	if err != nil {
		logger.Warn("fail to init resultReporter:%s", err.Error())
		resultReport.Disable = true
		return nil, errors.WithMessage(err, "fail to init resultReporter")
	}
	statusReport, err := reportlog.NewReporter(reportDir, "binlog_status.log", &logOpt)
	if err != nil {
		logger.Warn("fail to init statusReporter:%s", err.Error())
		statusReport.Disable = true
		return nil, errors.WithMessage(err, "fail to init statusReporter")
	}
	return &RotateReporters{
		Result: *resultReport,
		Status: *statusReport,
	}, nil
}
