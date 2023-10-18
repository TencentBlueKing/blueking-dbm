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
	"regexp"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/utils"

	"github.com/pkg/errors"
)

var tableSizeMetricName string
var dbSizeMetricName string

var tendbClusterDbNamePattern *regexp.Regexp

func init() {
	tableSizeMetricName = "mysql_table_size"
	dbSizeMetricName = "mysql_database_size"

	tendbClusterDbNamePattern = regexp.MustCompile(`^(.*)_[0-9]+$`)
}

func reportMetrics(result map[string]map[string]int64) error {
	for dbName, dbInfo := range result {
		var dbSize int64
		originalDbName := dbName

		// 根据 dbm 枚举约定, remote 是 tendbcluster 的存储机器类型
		if config.MonitorConfig.MachineType == "remote" {
			match := tendbClusterDbNamePattern.FindStringSubmatch(dbName)
			if match == nil {
				err := errors.Errorf(
					"invalid dbname: '%s' on %s",
					dbName, config.MonitorConfig.MachineType,
				)
				slog.Error("ibd-statistic report", slog.String("error", err.Error()))
				return err
			}
			dbName = match[1]
		}

		for tableName, tableSize := range dbInfo {
			utils.SendMonitorMetrics(
				tableSizeMetricName,
				tableSize,
				map[string]interface{}{
					"table_name":             tableName,
					"database_name":          dbName,
					"original_database_name": originalDbName,
				},
			)

			dbSize += tableSize
		}
		utils.SendMonitorMetrics(
			dbSizeMetricName,
			dbSize,
			map[string]interface{}{
				"database_name":          dbName,
				"original_database_name": originalDbName,
			},
		)
	}
	return nil
}
