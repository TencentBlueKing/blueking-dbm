// Package report TODO
package report

import (
	reapi "dbm-services/common/reverseapi/apis/common"
	recore "dbm-services/common/reverseapi/pkg/core"
	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbmon/pkg/models"
	"encoding/json"
	"fmt"
	"path/filepath"
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
	// 上报时去掉绝对路径, 只保留 binlog 文件名;
	// 本地 sqlite 记录与本地文件操作(删除过期备份等)仍使用完整路径
	reportData := *r
	if reportData.BackupFile != "" {
		reportData.BackupFile = filepath.Base(reportData.BackupFile)
	}
	reportRow := RedisBinlogReportSch{
		RedisBinlogHistorySchema: reportData,
		StartTime:                reportData.StartTime.Local().Format(time.RFC3339),
		EndTime:                  reportData.EndTime.Local().Format(time.RFC3339),
	}
	tmpBytes, _ := json.Marshal(reportRow)
	reporter.AddRecord(string(tmpBytes)+"\n", true)

	// 备份上报2.0 通道
	reverseConfig := common.GetResrveAPIConfig()
	reportCore, err := recore.NewCoreWithAddrsFile(reportData.BkCloudID, reverseConfig)
	if err != nil {
		return fmt.Errorf("report NewCore failed: %s", err.Error())
	}
	ev := RedisBinlogResultEvent(reportData)
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

// RedisBackupProgressReport 上报全备进度到 reverse api 2.0 通道.
// reporter 非空时同时写一份本地 report 文件, 作为 Kafka 不可达时的兜底.
func RedisBackupProgressReport(r *models.RedisFullbackupHistorySchema, reporter Reporter) error {
	if reporter != nil {
		reportRow := RedisFullBackupReportSch{
			RedisFullbackupHistorySchema: *r,
			StartTime:                    r.StartTime.Local().Format(time.RFC3339),
			EndTime:                      r.EndTime.Local().Format(time.RFC3339),
		}
		tmpBytes, _ := json.Marshal(reportRow)
		reporter.AddRecord(string(tmpBytes)+"\n", true)
	}

	reverseConfig := common.GetResrveAPIConfig()
	reportCore, err := recore.NewCoreWithAddrsFile(r.BkCloudID, reverseConfig)
	if err != nil {
		return fmt.Errorf("report NewCore failed: %s", err.Error())
	}
	ev := RedisBackupProgressEvent(*r)
	if resp, err := reapi.SyncReport(reportCore, &ev); err != nil {
		return fmt.Errorf("report fullbackup progress failed:%s, resp=%s", err.Error(), string(resp))
	}
	return nil
}
