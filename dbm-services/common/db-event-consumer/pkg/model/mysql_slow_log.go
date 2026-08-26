// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package model

import (
	"fmt"
	"log/slog"
	"strconv"
	"sync"
	"time"

	"github.com/coocood/freecache"
	json "github.com/goccy/go-json"
	sb "github.com/huandu/go-sqlbuilder"
	"github.com/pkg/errors"
	"github.com/spf13/cast"
	"gorm.io/gorm"

	"dbm-services/common/db-event-consumer/pkg/base"
	"dbm-services/common/db-event-consumer/pkg/sinker"
)

// slowLogDbNameCache 用于缓存每个实例当前上下文的 db_name。
// 10万实例，每个 key 约 30 字节（ip:port），value 约 64 字节（db_name），
// 分配 64MB 足够存储所有实例的上下文信息。
var slowLogDbNameCache *freecache.Cache
var slowLogCacheOnce sync.Once

// slowlog file 我们一天会 flush 一次
const slowLogDbNameExpireSec = 86400 * 2 // 48小时

// initSlowLogDbNameCache 初始化 slowLogDbNameCache 并启动定时状态打印
func initSlowLogDbNameCache() {
	slowLogCacheOnce.Do(func() {
		slowLogDbNameCache = freecache.NewCache(64 * 1024 * 1024)
		go func() {
			ticker := time.NewTicker(1 * time.Hour)
			defer ticker.Stop()
			for range ticker.C {
				slog.Info("slowLogDbNameCache stats",
					slog.Int64("entry_count", slowLogDbNameCache.EntryCount()),
					slog.Int64("evacuate_count", slowLogDbNameCache.EvacuateCount()),
					slog.Int64("hit_count", slowLogDbNameCache.HitCount()),
					slog.Int64("miss_count", slowLogDbNameCache.MissCount()),
					slog.Float64("hit_rate", slowLogDbNameCache.HitRate()),
					slog.Int64("overwrite_count", slowLogDbNameCache.OverwriteCount()),
					slog.Int64("lookup_count", slowLogDbNameCache.LookupCount()),
				)
			}
		}()
	})
}

type MysqlSlowLogModel struct {
	//ID uint `gorm:"primaryKey;autoIncrement:true"`
	// DtEventTimeStamp 2026-03-10 16:27:07
	DtEventTimeStamp time.Time `gorm:"column:dteventtimestamp;type:timestamp;not null" json:"dteventtimestamp" db:"dteventtimestamp"`
	// DtEventTimeHour	'2020-01-01 01:00:00'
	DtEventTimeHour string `gorm:"column:dteventtimehour;type:varchar(127);not null" json:"dteventtimehour" db:"dteventtimehour"`
	// LogTime	2026-03-10 16:27:07
	LogTime time.Time `gorm:"column:log_time;type:datetime;not null" json:"log_time" db:"log_time"`
	// SqlTimestamp	1773131220
	SqlTimestamp uint `gorm:"column:sql_timestamp;type:bigint;not null" json:"sql_timestamp" db:"sql_timestamp"`
	// TheDate 20250101
	TheDate int `gorm:"column:thedate;type:int;not null" json:"thedate" db:"thedate"`

	ClusterDomain string `gorm:"column:cluster_domain;type:varchar(255);not null" json:"cluster_domain" db:"cluster_domain"`
	InstanceHost  string `gorm:"column:instance_host;type:varchar(60);not null" json:"instance_host" db:"instance_host"`
	InstancePort  int    `gorm:"column:instance_port;type:int;not null" json:"instance_port" db:"instance_port"`
	InstanceRole  string `gorm:"column:instance_role;type:varchar(60);not null" json:"instance_role" db:"instance_role"`
	ClusterType   string `gorm:"column:cluster_type;type:varchar(60);not null" json:"cluster_type" db:"cluster_type"`

	QueryTime    float32 `gorm:"column:query_time;type:float;not null" json:"query_time" db:"query_time"`
	LockTime     float32 `gorm:"column:lock_time;type:float;not null" json:"lock_time" db:"lock_time"`
	RowsExamined int64   `gorm:"column:rows_examined;type:int;not null" json:"rows_examined" db:"rows_examined"`
	RowsSent     int64   `gorm:"column:rows_sent;type:int;not null" json:"rows_sent" db:"rows_sent"`

	QueryDigestMd5  string `gorm:"column:query_digest_md5;type:varchar(60);not null" json:"query_digest_md5" db:"query_digest_md5"`
	QueryDigestText string `gorm:"column:query_digest_text;type:text;not null" json:"query_digest_text" db:"query_digest_text"`
	QueryString     string `gorm:"column:query_string;type:longtext;not null" json:"query_string" db:"query_string"`
	QueryLength     int    `gorm:"column:query_length;type:int;not null" json:"query_length" db:"query_length"`
	QueryCommand    string `gorm:"column:query_command;type:varchar(60);not null" json:"command" db:"query_command"`
	TableNames      string `gorm:"column:table_names;type:varchar(1024);not null" json:"table_names" db:"table_names"`
	QueryDbName     string `gorm:"column:query_db_name;type:varchar(255);not null" json:"query_db_name" db:"query_db_name"`
	// DbName: Schema 最权威，其次是 DbName,最后是 QueryDbName
	DbName    string `gorm:"column:db_name;type:varchar(255);not null" json:"db_name" db:"db_name"`
	SessionId int64  `gorm:"column:session_id;type:bigint;not null" json:"session_id" db:"session_id"`
	// QueryStartTs SqlTimestamp
	// QueryStartTs uint `gorm:"column:query_start_ts;type:bigint;not null" json:"query_start_ts" db:"query_start_ts"`

	Username     string `gorm:"column:username;type:varchar(127);not null" json:"user" db:"username"`
	ClientHost   string `gorm:"column:client_host;type:varchar(60);not null" json:"client_host" db:"client_host"`
	AppName      string `gorm:"column:app_name;type:varchar(60);not null" json:"app" db:"app_name"`
	BkBizId      int    `gorm:"column:bk_biz_id;type:int;not null" json:"app_id" db:"bk_biz_id"`
	BkCloudId    int    `gorm:"column:bk_cloud_id;type:int;not null" json:"bk_cloud_id" db:"bk_cloud_id"`
	ParseFailure int    `gorm:"column:parse_failure;type:int;not null" json:"parse_failure" db:"parse_failure"`
}

type MysqlSlowLogMsg struct {
	Ext   DimExt `json:"ext"`
	Items []struct {
		Data           json.RawMessage        `json:"data"`
		Log            map[string]interface{} `json:"log"`
		Iterationindex int                    `json:"iterationindex"`
	} `json:"items"`

	Filename string    `json:"filename"`
	BkHostId int       `json:"bk_host_id"`
	Ip       string    `json:"ip"`
	Ts       int       `json:"time"`
	LogTime  time.Time `json:"datetime"`
	UtcTime  time.Time `json:"utc_time"`
}

type DimExt struct {
	BkBizId       string `json:"app_id"`
	AppName       string `json:"app"`
	BkCloudId     string `json:"bk_cloud_id"`
	ClusterDomain string `json:"cluster_domain"`
	InstanceHost  string `json:"instance_host"`
	InstancePort  string `json:"instance_port"`
	InstanceRole  string `json:"instance_role"`
	ClusterType   string `json:"cluster_type"`
}

type SlowLog struct {
	Username   string `json:"username"`
	ClientHost string `json:"client_host"`
	// Schema Schema: or Use xxx
	Schema string `json:"schema"`
	// DbName 与 Schema 字段等价
	DbName       string  `json:"db_name"`
	QueryTime    float32 `json:"query_time"`
	LockTime     float32 `json:"lock_time"`
	RowsExamined int64   `json:"rows_examined"`
	RowsSent     int64   `json:"rows_sent"`
	// SqlTimestamp	set timestamp=xxxx
	// # Time: 260309 12:57:05
	SqlTimestamp    uint   `json:"sql_timestamp"`
	QueryString     string `json:"query_string"`
	QueryDigestText string `json:"query_digest_text"`
	QueryDigestMd5  string `json:"query_digest_md5"`
	QueryCommand    string `json:"query_command"`
	QueryLength     int    `json:"query_length"`
	// QueryDbName parsed from query_string, 只是为了补充 Schema/DbName
	QueryDbName  string `json:"query_db_name"`
	TableNames   string `json:"table_names"`
	SessionId    int64  `json:"session_id"`
	QueryStartTs uint   `json:"query_start_ts"`
}

func (m *MysqlSlowLogModel) TableName() string {
	return "tb_mysql_slow_log2"
}

func (m *MysqlSlowLogModel) MigrateSchema(w base.DSWriter) error {
	initSlowLogDbNameCache()
	slog.Info("run migrate for MysqlSlowLogModel", slog.String("table", m.TableName()))
	dbWriter, ok := w.(base.GormMigrator)
	if !ok {
		return errors.Errorf("writer_type=%s has no gorm db for custom migrate: %s", w.Type(), m.TableName())
	}
	db := dbWriter.GormDB()
	if w.Type() == "mysql" || w.Type() == "mysql_raw" {
		createTableSql := CREATE_TABLE_SLOWLOG_MYSQL + BuildMysqlPartitionClause("dteventtimehour")
		if err := db.Exec(fmt.Sprintf(createTableSql, m.TableName())).Error; err != nil {
			slog.Error("create table failed", slog.Any("err", err), slog.String("sql", createTableSql))
			return err
		}
		return nil
	} else if w.Type() == "doris" || w.Type() == "doris_http" {
		if err := db.Exec(fmt.Sprintf(CREATE_TABLE_SLOWLOG_DORIS, m.TableName())).Error; err != nil {
			slog.Error("create table failed", slog.Any("err", err), slog.String("sql", CREATE_TABLE_SQL_DORIS))
			return err
		}
		return nil
	} else {
		return w.AutoMigrate(m)
	}
}

func (m *MysqlSlowLogModel) StrictSchema() bool {
	return true
}

func (m *MysqlSlowLogModel) Create(objs interface{}, w base.DSWriter) error {
	if writer, ok := w.(*sinker.DorisWriter); ok {
		return m.dorisCreate(objs, writer.GormDB())
	} else if writer, ok := w.(*sinker.DorisHttpWriter); ok {
		return m.dorisHttpCreate(objs, writer)
	} else if writer, ok := w.(*sinker.MysqlWriter); ok {
		return m.dorisCreate(objs, writer.GormDB())
	} else {
		//return errors.Errorf("not implement custom writer: %s", w.Type())
		// mysql writer?
		newObj := objs.([]MysqlSlowLogModel)
		return w.WriteBatch(m, newObj)
	}
}

func (m *MysqlSlowLogModel) dorisHttpCreate(i interface{}, w *sinker.DorisHttpWriter) error {
	kafkaObjs, ok := i.([]MysqlSlowLogModel)
	if !ok {
		kafkaObjs = []MysqlSlowLogModel{i.(MysqlSlowLogModel)}
	}
	return w.WriteBatch(m, kafkaObjs)
}

func (m *MysqlSlowLogModel) dorisCreate(i interface{}, db *gorm.DB) error {
	// 从 kafka msg 里面反序列化出来，可能是单个，也可能是批量
	// custom writer 反序列化出来，一半是具体的对象，不是 map (比较难处理)
	kafkaObjs, ok := i.([]MysqlSlowLogModel)
	if !ok {
		kafkaObjs = []MysqlSlowLogModel{i.(MysqlSlowLogModel)}
	}
	//fmt.Printf("xxxx create obj:%+v", kafkaObjs)
	builder := sb.NewInsertBuilder()
	builder.InsertInto(m.TableName())
	builder.Cols(
		"dteventtimehour", "dteventtimestamp", "log_time", "thedate",
		"cluster_domain",
		"instance_host",
		"instance_port",
		"instance_role",

		"query_digest_md5",
		"query_digest_text",
		"query_string",
		"query_length",
		"query_command",
		"query_db_name",
		"db_name",
		"table_names",

		"query_time",
		"lock_time",
		"rows_examined",
		"rows_sent",

		"session_id",
		"username",
		"client_host",
		"cluster_type",
		"bk_biz_id",
		"app_name",
		"bk_cloud_id",
		"parse_failure",
	)

	for _, kafkaObj := range kafkaObjs {
		// slog.Debug("unmarshal task obj", slog.Any("obj", kafkaObj))
		builder.Values(
			kafkaObj.DtEventTimeHour, kafkaObj.DtEventTimeStamp, kafkaObj.LogTime, kafkaObj.TheDate,
			kafkaObj.ClusterDomain,
			kafkaObj.InstanceHost,
			kafkaObj.InstancePort,
			kafkaObj.InstanceRole,

			kafkaObj.QueryDigestMd5,
			kafkaObj.QueryDigestText,
			kafkaObj.QueryString,
			kafkaObj.QueryLength,
			kafkaObj.QueryCommand,
			kafkaObj.QueryDbName,
			kafkaObj.DbName,
			kafkaObj.TableNames,

			kafkaObj.QueryTime,
			kafkaObj.LockTime,
			kafkaObj.RowsExamined,
			kafkaObj.RowsSent,

			kafkaObj.SessionId,
			kafkaObj.Username,
			kafkaObj.ClientHost,
			kafkaObj.ClusterType,
			kafkaObj.BkBizId,
			kafkaObj.AppName,
			kafkaObj.BkCloudId,
			kafkaObj.ParseFailure,
		)
	}

	sqlStr, sqlArgs := builder.Build()
	sqlFull, err := sb.Doris.Interpolate(sqlStr, sqlArgs)
	if err != nil {
		return err
	}
	err = db.Exec(sqlFull).Error
	if err != nil {
		slog.Error("replace message",
			slog.Any("msg", err), slog.String("sql", sqlFull))
		//return err
	}
	return nil
}

var CREATE_TABLE_SLOWLOG_MYSQL = `
CREATE TABLE IF NOT EXISTS %s (
  id bigint NOT NULL AUTO_INCREMENT,
  cluster_domain varchar(200) NOT NULL,
  instance_role varchar(60) DEFAULT NULL,
  dteventtimehour datetime NOT NULL COMMENT 'datetime precision to hour, used as where,group-by,expire',
  dteventtimestamp datetime NOT NULL,
  sql_timestamp int NULL,
  thedate int NOT NULL,
  log_time datetime NULL,
  query_digest_md5 varchar(60) DEFAULT NULL,
  instance_host varchar(60) DEFAULT NULL,
  instance_port int DEFAULT NULL,
  shard_value int DEFAULT NULL,
  cluster_type varchar(60) DEFAULT NULL,

  query_time float DEFAULT NULL,
  lock_time float DEFAULT NULL,
  rows_examined bigint DEFAULT NULL,
  rows_sent bigint DEFAULT NULL,
  query_digest_text longtext DEFAULT NULL,
  query_string longtext DEFAULT NULL,
  query_length int DEFAULT NULL,
  query_command varchar(60) DEFAULT NULL,
  query_db_name varchar(127) DEFAULT NULL,
  table_names varchar(1024) DEFAULT NULL,
  db_name varchar(100) DEFAULT NULL,
  table_name varchar(100) DEFAULT NULL,
    
  bk_biz_id int DEFAULT NULL,
  bk_cloud_id int DEFAULT NULL,
  session_id bigint DEFAULT NULL,
  client_host varchar(60) DEFAULT NULL,
  username varchar(127) DEFAULT NULL,
  app_name varchar(60) DEFAULT NULL,
  parse_failure int DEFAULT NULL,
  PRIMARY KEY (cluster_domain,dteventtimehour,id),
  KEY idx_0 (id),
  KEY idx_1 (cluster_domain,dteventtimestamp),
  KEY idx_2 (dteventtimehour,cluster_domain),
  KEY idx_3 (query_digest_md5),
  KEY idx_4 (instance_host,instance_port)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 
`

var CREATE_TABLE_SLOWLOG_DORIS = `
CREATE TABLE IF NOT EXISTS %s (
  cluster_domain varchar(255) NOT NULL,
  instance_role varchar(60) NULL,
  query_digest_md5 varchar(100) NULL,
  dteventtimehour datetime NOT NULL COMMENT "datetime precision to hour, used as where,group-by,expire",
  
  dteventtimestamp datetime NOT NULL,
  sql_timestamp int NULL,
  thedate int NULL,
  log_time datetime NULL,
  instance_host varchar(60) NULL,
  instance_port int NULL,

  query_time float NULL,
  lock_time float NULL,
  rows_examined bigint NULL,
  rows_sent bigint NULL,
    
  query_digest_text string NULL,
  query_string string NULL,
  query_length int NULL,
  query_command varchar(60) NULL,
  query_db_name varchar(100) NULL,
  db_name varchar(100) NULL,
  table_names varchar(1024) NULL,

  session_id bigint NULL,
  client_host varchar(60) NULL,
  username varchar(60) NULL,
  cluster_type varchar(60) NULL,
  bk_cloud_id int NULL,
  bk_biz_id int NULL,
  app_name varchar(60) NULL,
  parse_failure int NULL,
) ENGINE=OLAP
DUPLICATE KEY(cluster_domain, instance_role, query_digest_md5, dteventtimehour)
PARTITION BY RANGE(dteventtimehour)()
DISTRIBUTED BY HASH(cluster_domain) BUCKETS 12
PROPERTIES (
  "replication_allocation" = "tag.location.default: 1",
  "min_load_replica_num" = "-1",
  "bloom_filter_columns" = "cluster_domain, instance_host,bk_biz_id, query_digest_md5",
  "is_being_synced" = "false",
  "dynamic_partition.enable" = "true",
  "dynamic_partition.time_unit" = "DAY",
  "dynamic_partition.time_zone" = "Asia/Shanghai",
  "dynamic_partition.start" = "-30",
  "dynamic_partition.end" = "2",
  "dynamic_partition.prefix" = "p",
  "dynamic_partition.replication_allocation" = "tag.location.default: 1",
  "dynamic_partition.buckets" = "12",
  "dynamic_partition.create_history_partition" = "true",
  "dynamic_partition.history_partition_num" = "7",
  "dynamic_partition.hot_partition_num" = "0",
  "dynamic_partition.reserved_history_periods" = "NULL",
  "dynamic_partition.storage_policy" = "",
  "storage_medium" = "ssd",
  "storage_format" = "V2",
  "inverted_index_storage_format" = "V2",
  "light_schema_change" = "true",
  "disable_auto_compaction" = "false",
  "enable_single_replica_compaction" = "false",
  "group_commit_interval_ms" = "10000",
  "group_commit_data_bytes" = "134217728"
);
`

func (m *MysqlSlowLogModel) UnmarshalItem(data []byte, msg base.MessageWrapper) error {
	// 用 json.Unmarshal 直接解引号，比 strconv.Unquote(string(data)) 少一次 []byte→string 的内存分配
	var queryString string
	if err := json.Unmarshal(data, &queryString); err != nil || queryString == "" {
		return fmt.Errorf("invalid data: %s", data)
	}
	logParsed, err := parseOneSlowLog(queryString, true)
	if err != nil {
		return errors.WithMessagef(err, "parse slow log failed: %s", queryString)
	}

	// 直接赋值替代 copier.Copy(m, logParsed)，消除反射开销和临时对象分配
	m.Username = logParsed.Username
	m.ClientHost = logParsed.ClientHost
	m.QueryTime = logParsed.QueryTime
	m.LockTime = logParsed.LockTime
	m.RowsExamined = logParsed.RowsExamined
	m.RowsSent = logParsed.RowsSent
	m.SqlTimestamp = logParsed.SqlTimestamp
	m.QueryString = logParsed.QueryString
	m.QueryDigestText = logParsed.QueryDigestText
	m.QueryDigestMd5 = logParsed.QueryDigestMd5
	m.QueryCommand = logParsed.QueryCommand
	m.QueryLength = logParsed.QueryLength
	m.QueryDbName = logParsed.QueryDbName
	m.DbName = logParsed.DbName
	m.TableNames = logParsed.TableNames
	m.SessionId = logParsed.SessionId
	// m.QueryStartTs = logParsed.QueryStartTs

	// 直接从 msg.Ext 提取维度字段，替代 mapstructure.Decode + copier.Copy，
	// 避免每条消息创建 DimExt、DecoderConfig、Decoder 等临时对象
	if msg.Ext != nil {
		m.BkBizId = cast.ToInt(msg.Ext["app_id"])
		m.BkCloudId = cast.ToInt(msg.Ext["bk_cloud_id"])
		m.ClusterDomain = cast.ToString(msg.Ext["cluster_domain"])
		m.InstanceHost = cast.ToString(msg.Ext["instance_host"])
		m.InstancePort = cast.ToInt(msg.Ext["instance_port"])
		m.InstanceRole = cast.ToString(msg.Ext["instance_role"])
		m.ClusterType = cast.ToString(msg.Ext["cluster_type"])
		m.AppName = cast.ToString(msg.Ext["app"])
	}

	m.GetSchemaFromContext()

	m.DtEventTimeStamp = msg.LogTime.Time
	m.LogTime = msg.UtcTime.Time

	m.TheDate, _ = strconv.Atoi(m.LogTime.Format("20060102"))
	m.DtEventTimeHour = m.LogTime.Format("2006-01-02 15")

	return nil
}

// GetSchemaFromContext 当慢查询段中没有 USE db 或 Schema 为空时，从缓存中获取上一次的 db_name
// 使用 freecache 维护每个实例的上下文 db_name
func (m *MysqlSlowLogModel) GetSchemaFromContext() {
	// 使用 freecache 维护每个实例的上下文 db_name
	// 当慢查询段中没有 USE db 或 Schema 为空时，从缓存中获取上一次的 db_name
	instanceKey := []byte(fmt.Sprintf("%s:%d", m.InstanceHost, m.InstancePort))
	if m.DbName != "" {
		// 当前慢查询解析出了 db_name（来自 Schema: 或 USE db），更新缓存
		_ = slowLogDbNameCache.Set(instanceKey, []byte(m.DbName), slowLogDbNameExpireSec)
		// TODO 需要测试下 freecache 读/写的性能。如果写性能差，建议改成先读，如果 DbName 不一样才 set
	} else {
		// 当前慢查询没有 db_name，尝试从缓存中获取该实例上下文的 db_name
		if cachedDb, err := slowLogDbNameCache.Get(instanceKey); err == nil && len(cachedDb) > 0 {
			m.DbName = string(cachedDb)
		}
	}
}
