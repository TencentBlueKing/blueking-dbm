// Package report TODO
package report

import (
	reapi "dbm-services/common/reverseapi/apis/common"
	recore "dbm-services/common/reverseapi/pkg/core"
	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbmon/pkg/models"
	"encoding/json"
	"fmt"
	"time"
)

type RedisBinlogReportSch struct {
	models.RedisBinlogHistorySchema
	StartTime string `json:"start_time"`
	EndTime   string `json:"end_time"`
}

// BackupRecordReport 备份记录上报
func RedisBinlogReport(r *models.RedisBinlogHistorySchema, reporter Reporter) error {
	if reporter == nil {
		return fmt.Errorf("report is Nil, will not report fullback")
	}
	reportRow := RedisBinlogReportSch{
		RedisBinlogHistorySchema: *r,
		StartTime:                r.StartTime.Local().Format(time.RFC3339),
		EndTime:                  r.EndTime.Local().Format(time.RFC3339),
	}
	tmpBytes, _ := json.Marshal(reportRow)
	reporter.AddRecord(string(tmpBytes)+"\n", true)

	// 备份上报2.0 通道
	reverseConfig := common.GetResrveAPIConfig()
	reportCore, err := recore.NewCoreWithAddrsFile(r.BkCloudID, reverseConfig)
	if err != nil {
		return fmt.Errorf("report NewCore failed: %s", err.Error())
	}
	ev := RedisBinlogResultEvent(*r)
	if resp, err := reapi.SyncReport(reportCore, &ev); err != nil {
		return fmt.Errorf("report binlog status failed:%s, resp=%s", err.Error(), string(resp))
	}
	return nil
}

type RedisFullBackupReportSch struct {
	models.RedisFullbackupHistorySchema
	StartTime string `json:"start_time"`
	EndTime   string `json:"end_time"`
}

// BackupRecordReport 备份记录上报
func RedisFullBackupReport(r *models.RedisFullbackupHistorySchema, reporter Reporter) error {
	if reporter == nil {
		return fmt.Errorf("report is Nil, will not report fullback")
	}
	reportRow := RedisFullBackupReportSch{
		RedisFullbackupHistorySchema: *r,
		StartTime:                    r.StartTime.Local().Format(time.RFC3339),
		EndTime:                      r.EndTime.Local().Format(time.RFC3339),
	}
	tmpBytes, _ := json.Marshal(reportRow)
	reporter.AddRecord(string(tmpBytes)+"\n", true)

	// 备份上报2.0 通道
	reverseConfig := common.GetResrveAPIConfig()
	reportCore, err := recore.NewCoreWithAddrsFile(r.BkCloudID, reverseConfig)
	if err != nil {
		return fmt.Errorf("report NewCore failed: %s", err.Error())
	}
	ev := RedisFullBackupResultEvent(*r)
	if resp, err := reapi.SyncReport(reportCore, &ev); err != nil {
		return fmt.Errorf("report fullbackup status failed:%s, resp=%s", err.Error(), string(resp))
	}
	return nil
}
