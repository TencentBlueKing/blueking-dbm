package report

import (
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/models"
	"encoding/json"
	"fmt"
	"strconv"
	"time"
)

// parseBkBizID 将字符串形式的 bk_biz_id 解析为 int64,
// 解析失败时以 warn 级别记录日志并返回 0, 避免脏数据静默落库难以排障.
func parseBkBizID(eventType, rawBkBizID string) int64 {
	if rawBkBizID == "" {
		mylog.Logger.Warn(fmt.Sprintf("event(%s) bk_biz_id is empty, will fallback to 0", eventType))
		return 0
	}
	bkbizID, err := strconv.ParseInt(rawBkBizID, 10, 64)
	if err != nil {
		mylog.Logger.Warn(fmt.Sprintf(
			"event(%s) parse bkBizID:%s 2 int64 failed:%+v, will fallback to 0",
			eventType, rawBkBizID, err))
		return 0
	}
	return bkbizID
}

// binlog backup event.
type RedisBinlogResultEvent models.RedisBinlogHistorySchema

func (e *RedisBinlogResultEvent) ClusterType() string {
	return getEventReporteClusterType(e.DbType)
}

func (e *RedisBinlogResultEvent) EventType() string {
	return "redis_binlog_result"
}

// EventCreateTime 使用 binlog 文件生成时间(StartTime)作为事件时间,
// 保证同一 binlog 多次状态上报时事件时间稳定,避免与"上报时间"混淆.
func (e *RedisBinlogResultEvent) EventCreateTime() time.Time {
	if e.StartTime.IsZero() {
		return time.Now()
	}
	return e.StartTime
}

func (e *RedisBinlogResultEvent) EventBkBizId() int64 {
	return parseBkBizID(e.EventType(), e.BkBizID)
}

// 不强求实现 String, 这里是给下面的错误处理写例子用的
func (e *RedisBinlogResultEvent) String() string {
	b, _ := json.Marshal(e)
	return string(b)
}

// full backup event.
type RedisFullBackupResultEvent models.RedisFullbackupHistorySchema

func (e *RedisFullBackupResultEvent) ClusterType() string {
	return getEventReporteClusterType(e.DbType)
}

func (e *RedisFullBackupResultEvent) EventType() string {
	return "redis_backup_result"
}

// EventCreateTime 使用备份开始时间(StartTime)作为事件时间,
// 使同一次备份的多次状态上报共享稳定的 event_create_timestamp.
func (e *RedisFullBackupResultEvent) EventCreateTime() time.Time {
	if e.StartTime.IsZero() {
		return time.Now()
	}
	return e.StartTime
}

func (e *RedisFullBackupResultEvent) EventBkBizId() int64 {
	return parseBkBizID(e.EventType(), e.BkBizID)
}

// 不强求实现 String, 这里是给下面的错误处理写例子用的
func (e *RedisFullBackupResultEvent) String() string {
	b, _ := json.Marshal(e)
	return string(b)
}

type redisBackupProgressPayload struct {
	Status         string `json:"status"`
	StatusDetail   string `json:"status_detail"`
	BackupId       string `json:"backup_task_id"`
	BackupType     string `json:"backup_type"`
	BackupIdentify string `json:"backup_identify"`
	ImmuteDomain   string `json:"immute_domain"`
	BackupHost     string `json:"backup_host"`
	BackupPort     int    `json:"backup_port"`
	RedisRole      string `json:"redis_role"`
	ShardValue     string `json:"shard_value"`
	BkBizId        string `json:"bk_biz_id"`
	IsFullBackup   bool   `json:"is_full_backup"`
}

// RedisBackupProgressEvent full backup progress event.
type RedisBackupProgressEvent models.RedisFullbackupHistorySchema

func (e *RedisBackupProgressEvent) ClusterType() string {
	return getEventReporteClusterType(e.DbType)
}

func (e *RedisBackupProgressEvent) EventType() string {
	return "redis_backup_progress"
}

// EventCreateTime progress 事件以"进度发生时刻"为事件时间(即上报当下),
// 与 RedisFullBackupResultEvent 用 StartTime 不同, 请注意区分.
func (e *RedisBackupProgressEvent) EventCreateTime() time.Time {
	return time.Now()
}

func (e *RedisBackupProgressEvent) EventBkBizId() int64 {
	return parseBkBizID(e.EventType(), e.BkBizID)
}

func (e *RedisBackupProgressEvent) MarshalJSON() ([]byte, error) {
	return json.Marshal(redisBackupProgressPayload{
		Status:         e.Status,
		StatusDetail:   e.Message,
		BackupId:       e.BackupTaskID,
		BackupType:     e.ReportType,
		BackupIdentify: e.BackupIdentify,
		ImmuteDomain:   e.Domain,
		BackupHost:     e.ServerIP,
		BackupPort:     e.ServerPort,
		RedisRole:      e.RealRole,
		ShardValue:     e.ShardValue,
		BkBizId:        e.BkBizID,
		IsFullBackup:   true,
	})
}

// 不强求实现 String, 这里是给下面的错误处理写例子用的
func (e *RedisBackupProgressEvent) String() string {
	b, _ := json.Marshal(e)
	return string(b)
}

// 转换一下类型  .
func getEventReporteClusterType(c string) string {
	return c
	// class ClusterType(StrStructuredEnum) :
}
