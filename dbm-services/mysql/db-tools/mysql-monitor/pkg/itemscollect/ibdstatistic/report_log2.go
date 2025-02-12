// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package ibdstatistic

import (
	"log/slog"
	"os"
	"path/filepath"
	"slices"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/reportlog"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/internal/cst"

	"github.com/pkg/errors"
)

func reportLog2(dbTableSize map[string]int64, dbSize map[string]int64) error {
	dbsizeReportBaseDir := filepath.Join(cst.DBAReportBase, "mysql/dbsize")
	err := os.MkdirAll(dbsizeReportBaseDir, os.ModePerm)
	if err != nil {
		slog.Error("failed to create database size reports directory", slog.String("error", err.Error()))
		return errors.Wrap(err, "failed to create database size reports directory")
	}
	// TODO add port to report_<port>.log
	resultReport, err := reportlog.NewReporter(dbsizeReportBaseDir, "report.log", nil)
	if err != nil {
		return err
	}
	reportTs := cmutil.TimeToSecondPrecision(time.Now())
	for dbTableName, tableSize := range dbTableSize {
		var originalDBName, tableName string
		if originalDBName, tableName, err = cmutil.GetDbTableName(dbTableName); err != nil {
			return err
		}
		if _, ok := dbSize[originalDBName]; !ok { // 这个不应该发生，防止后面 panic 设置默认值
			slog.Error("failed to read database size for db %s", originalDBName)
			dbSize[originalDBName] = 0
		}
		// 根据 dbm 枚举约定, remote 是 tendbcluster 的存储机器类型
		// originalDBName 是 remote/backend 上的真实 db名
		// dbName 是 业务看到的 db 名（去掉 remote shard后缀）
		dbName := originalDBName
		if dbTableName == cst.OTHER_DB_TABLE_NAME {
			dbSize[originalDBName] = tableSize
		}

		if slices.Index(systemDBs, dbName) >= 0 {
			continue
		} else if config.MonitorConfig.MachineType == "remote" {
			// 针对 spider remote 转换 dbName
			match := tenDBClusterDbNamePattern.FindStringSubmatch(originalDBName)
			if match == nil {
				err := errors.Errorf(
					"invalid dbname: '%s' on %s",
					originalDBName, config.MonitorConfig.MachineType,
				)
				slog.Warn("ibd-statistic report", slog.String("error", err.Error()))
				// 这里不退出，尽可能上报  dbTableName == "_OTHER_._OTHER_"
				//return err
			} else {
				dbName = match[1]
			}
		}

		oneTableInfo := tableSizeStruct{
			BkCloudId:         *config.MonitorConfig.BkCloudID,
			BkBizId:           config.MonitorConfig.BkBizId,
			ImmuteDomain:      config.MonitorConfig.ImmuteDomain,
			DBModule:          *config.MonitorConfig.DBModuleID,
			MachineType:       config.MonitorConfig.MachineType,
			Ip:                config.MonitorConfig.Ip,
			Port:              config.MonitorConfig.Port,
			Role:              *config.MonitorConfig.Role,
			ServiceInstanceId: config.MonitorConfig.BkInstanceId,
			OriginalDBName:    originalDBName,
			DBName:            dbName,
			DBSize:            dbSize[originalDBName], // 每个表都会跟随上报一份 database size
			TableName:         tableName,
			TableSize:         tableSize,
			ReportTime:        reportTs,
		}
		resultReport.Println(oneTableInfo)
	}
	return nil
}
