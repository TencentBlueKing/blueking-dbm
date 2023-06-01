package ibd_statistic

import (
	"regexp"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/utils"

	"github.com/pkg/errors"
	"golang.org/x/exp/slog"
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
				slog.Error("ibd-statistic report", err)
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
