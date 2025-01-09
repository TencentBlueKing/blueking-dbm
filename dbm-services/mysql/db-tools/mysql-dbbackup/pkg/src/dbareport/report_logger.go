/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

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
var reportLogger = &ReportLogger{}

// InitReporter TODO
func InitReporter(reportDir string) (err error) {
	if reportDir == "" {
		logger.Log.Warnf("do not report backup result to reportDir=%s", reportDir)
		reportLogger.Files = reportlog.Reporter{Disable: true}
		reportLogger.Result = reportlog.Reporter{Disable: true}
		return nil
	}
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
		MaxSize:    100,
		MaxBackups: 10,
		MaxAge:     60,
		Compress:   true,
	}
	resultReport, err := reportlog.NewReporter(reportDir, "backup_result.log", &logOpt)
	if err != nil {
		logger.Log.Warn("fail to init resultReporter:", err.Error())
		return nil, errors.WithMessage(err, "fail to init resultReporter")
	}
	filesReport, err := reportlog.NewReporter(filepath.Join(reportDir, "result"), "dbareport_result.log", &logOpt)
	if err != nil {
		logger.Log.Warn("fail to init statusReporter:", err.Error())
		//filesReport.Disable = true
		return nil, errors.WithMessage(err, "fail to init statusReporter")
	}
	statusReport, err := reportlog.NewReporter(filepath.Join(reportDir, "status"), "backup_status.log", &logOpt)
	if err != nil {
		logger.Log.Warn("fail to init statusReporter:", err.Error())
		//statusReport.Disable = true
		return nil, errors.WithMessage(err, "fail to init statusReporter")
	}
	return &ReportLogger{
		Result: *resultReport,
		Files:  *filesReport,
		Status: *statusReport,
	}, nil
}
