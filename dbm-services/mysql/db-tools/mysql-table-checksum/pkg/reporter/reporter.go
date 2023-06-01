// Package reporter 上报
package reporter

import (
	"path"

	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"

	"gopkg.in/natefinch/lumberjack.v2"
)

// Reporter 上报bk log
type Reporter struct {
	writer *lumberjack.Logger
	cfg    *config.Config
}

// var reporter *lumberjack.Logger

// NewReporter 新建上报
func NewReporter(cfg *config.Config) *Reporter {
	return &Reporter{
		cfg: cfg,
		writer: &lumberjack.Logger{
			Filename:   path.Join(cfg.ReportPath, "checksum_report.log"),
			MaxSize:    100,
			MaxAge:     30,
			MaxBackups: 50,
		},
	}
}
