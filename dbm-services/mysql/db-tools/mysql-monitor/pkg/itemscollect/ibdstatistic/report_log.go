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

type tableSizeStruct struct {
	// ReportTime time.RFC3339, format like 024-11-29T11:19:02+08:00
	ReportTime        time.Time `json:"report_time"`
	BkCloudId         int       `json:"bk_cloud_id"`
	BkBizId           int       `json:"bk_biz_id"`
	ImmuteDomain      string    `json:"cluster_domain"`
	DBModule          int       `json:"db_module"`
	MachineType       string    `json:"machine_type"`
	Ip                string    `json:"instance_host"`
	Port              int       `json:"instance_port"`
	Role              string    `json:"instance_role"`
	ServiceInstanceId int64     `json:"bk_target_service_instance_id"`
	// OriginalDBName original DBName for spider remote(with shard_id suffix)
	OriginalDBName string `json:"original_database_name"`
	DBName         string `json:"database_name"`
	DBSize         int64  `json:"database_size"`
	TableName      string `json:"table_name"`
	TableSize      int64  `json:"table_size"`
}

func reportLog(result map[string]map[string]int64) error {
	dbsizeReportBaseDir := filepath.Join(cst.DBAReportBase, "mysql/dbsize")
	err := os.MkdirAll(dbsizeReportBaseDir, os.ModePerm)
	if err != nil {
		slog.Error("failed to create database size reports directory", slog.String("error", err.Error()))
		return errors.Wrap(err, "failed to create database size reports directory")
	}
	resultReport, err := reportlog.NewReporter(dbsizeReportBaseDir, "report.log", nil)
	if err != nil {
		return err
	}
	reportTs := cmutil.TimeToSecondPrecision(time.Now())
	for originalDBName, dbInfo := range result {
		// 根据 dbm 枚举约定, remote 是 tendbcluster 的存储机器类型
		dbName := originalDBName
		if config.MonitorConfig.MachineType == "remote" && slices.Index(systemDBs, originalDBName) < 0 {
			match := tenDBClusterDbNamePattern.FindStringSubmatch(originalDBName)
			if match == nil {
				err := errors.Errorf(
					"invalid dbname: '%s' on %s",
					originalDBName, config.MonitorConfig.MachineType,
				)
				slog.Error("ibd-statistic report", slog.String("error", err.Error()))
				return err
			}
			dbName = match[1]
		}

		var dbSize int64
		var tablesInfo []tableSizeStruct
		for tableName, tableSize := range dbInfo {
			tablesInfo = append(tablesInfo, tableSizeStruct{
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
				DBSize:            0,
				TableName:         tableName,
				TableSize:         tableSize,
			})
			dbSize += tableSize
		}

		for _, row := range tablesInfo {
			row.DBSize = dbSize
			row.ReportTime = reportTs
			if slices.Index(systemDBs, row.DBName) >= 0 {
				continue
			}
			resultReport.Println(row)
		}
	}
	return nil
}
