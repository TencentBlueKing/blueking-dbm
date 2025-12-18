package report

import (
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/pkg/models"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"
)

// binlog backup event.
type RedisBinlogResultEvent models.RedisBinlogHistorySchema

func (e *RedisBinlogResultEvent) ClusterType() string {
	return getEventReporteClusterType(e.DbType)
}

func (e *RedisBinlogResultEvent) EventType() string {
	return "redis_binlog_result"
}

func (e *RedisBinlogResultEvent) EventCreateTime() time.Time {
	return time.Now()
}

func (e *RedisBinlogResultEvent) EventBkBizId() int64 {
	bkbizID, err := strconv.ParseInt(e.BkBizID, 10, 64)
	if err != nil {
		fmt.Printf("parse bkBizID:%s 2 int64 failed:%+v", e.BkBizID)
	}
	return bkbizID
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

func (e *RedisFullBackupResultEvent) EventCreateTime() time.Time {
	return time.Now()
}

func (e *RedisFullBackupResultEvent) EventBkBizId() int64 {
	bkbizID, err := strconv.ParseInt(e.BkBizID, 10, 64)
	if err != nil {
		fmt.Printf("parse bkBizID:%s 2 int64 failed:%+v", e.BkBizID)
	}
	return bkbizID
}

// 不强求实现 String, 这里是给下面的错误处理写例子用的
func (e *RedisFullBackupResultEvent) String() string {
	b, _ := json.Marshal(e)
	return string(b)
}

// 转换一下类型  .
func getEventReporteClusterType(c string) string {
	targetClusterType := strings.ToLower(c)
	switch c {
	case consts.TendisTypeTwemproxyRedisInstance:
		targetClusterType = "tendis_cache"
	case consts.TendisTypeTendisSSDInsance:
		targetClusterType = "tendis_ssd"
	case consts.TendisTypePredixyTendisplusCluster:
		targetClusterType = "tendisplus"
	case consts.TendisTypePredixyRedisCluster:
		targetClusterType = "redis_cluster"
	case consts.TendisTypeRedisInstance:
		targetClusterType = "redis_single"
	}
	return targetClusterType
}
