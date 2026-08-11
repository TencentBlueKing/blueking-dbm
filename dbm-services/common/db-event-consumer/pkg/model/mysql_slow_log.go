// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package model

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"strconv"
	"strings"
	"time"

	"github.com/go-viper/mapstructure/v2"
	sb "github.com/huandu/go-sqlbuilder"
	"github.com/jinzhu/copier"
	"github.com/pkg/errors"
	"github.com/spf13/cast"
	"gorm.io/gorm"

	"dbm-services/common/db-event-consumer/pkg/base"
	"dbm-services/common/db-event-consumer/pkg/sinker"
	"dbm-services/common/go-pubpkg/cmutil"
)

type MysqlSlowLogModel struct {
	ID uint `gorm:"primaryKey;autoIncrement:true"`
	// DtEventTimeStamp 2026-03-10 16:27:07
	DtEventTimeStamp time.Time `gorm:"column:dteventtimestamp;type:timestamp;not null" json:"dteventtimestamp" db:"dteventtimestamp"`
	// DtEventTimeHour	'2020-01-01 01:00:00'
	DtEventTimeHour string `gorm:"column:dteventtimehour;type:varchar(127);not null" json:"dteventtimehour" db:"dteventtimehour"`
	// LogTime	2026-03-10 16:27:07
	LogTime time.Time `gorm:"column:log_time;type:datetime;not null" json:"time" db:"log_time"`
	// TheDate 20250101
	TheDate int `gorm:"column:thedate;type:int;not null" json:"thedate" db:"thedate"`

	ClusterDomain string `gorm:"column:cluster_domain;type:varchar(200);not null" json:"cluster_domain" db:"cluster_domain"`
	InstanceHost  string `gorm:"column:instance_host;type:varchar(60);not null" json:"instance_host" db:"instance_host"`
	InstancePort  int    `gorm:"column:instance_port;type:int;not null" json:"instance_port" db:"instance_port"`
	InstanceRole  string `gorm:"column:instance_role;type:varchar(60);not null" json:"instance_role" db:"instance_role"`
	ClusterType   string `gorm:"column:cluster_type;type:varchar(60);not null" json:"cluster_type" db:"cluster_type"`

	QueryTime    float32 `gorm:"column:query_time;type:float;not null" json:"query_time" db:"query_time"`
	LockTime     float32 `gorm:"column:lock_time;type:float;not null" json:"lock_time" db:"lock_time"`
	RowsExamined int     `gorm:"column:rows_examined;type:int;not null" json:"rows_examined" db:"rows_examined"`
	RowsSent     int     `gorm:"column:rows_sent;type:int;not null" json:"rows_sent" db:"rows_sent"`

	QueryDigestMd5  string `gorm:"column:query_digest_md5;type:varchar(60);not null" json:"query_digest_md5" db:"query_digest_md5"`
	QueryDigestText string `gorm:"column:query_digest_text;type:text;not null" json:"query_digest_text" db:"query_digest_text"`
	QueryString     string `gorm:"column:query_string;type:longtext;not null" json:"query_string" db:"query_string"`
	QueryLength     int    `gorm:"column:query_length;type:int;not null" json:"query_length" db:"query_length"`
	QueryCommand    string `gorm:"column:query_command;type:varchar(60);not null" json:"command" db:"query_command"`
	QueryDbName     string `gorm:"column:query_db_name;type:varchar(127);not null" json:"query_db_name" db:"query_db_name"`
	DbName          string `gorm:"column:db_name;type:varchar(127);not null" json:"db_name" db:"db_name"`
	TableNames      string `gorm:"column:table_names;type:varchar(1024);not null" json:"table_names" db:"table_names"`

	Username     string `gorm:"column:username;type:varchar(127);not null" json:"user" db:"username"`
	ClientHost   string `gorm:"column:client_host;type:varchar(60);not null" json:"client_host" db:"client_host"`
	AppName      string `gorm:"column:app_name;type:varchar(60);not null" json:"app" db:"app_name"`
	BkBizId      int    `gorm:"column:bk_biz_id;type:int;not null" json:"app_id" db:"bk_biz_id"`
	BkCloudId    int    `gorm:"column:bk_cloud_id;type:int;not null" json:"bk_cloud_id" db:"bk_cloud_id"`
	ParseFailure int    `gorm:"column:parse_failure;type:int;not null" json:"parse_failure" db:"parse_failure"`
	// SqlTimestamp	1773131220
	SqlTimestamp uint `gorm:"column:sql_timestamp;type:bigint;not null" json:"sql_timestamp" db:"sql_timestamp"`
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
	// DbName	Schema: or Use xxx
	DbName       string  `json:"db_name"`
	QueryTime    float32 `json:"query_time"`
	LockTime     float32 `json:"lock_time"`
	RowsExamined int     `json:"rows_examined"`
	RowsSent     int     `json:"rows_sent"`
	// SqlTimestamp	set timestamp=xxxx
	// # Time: 260309 12:57:05
	SqlTimestamp    uint   `json:"sql_timestamp"`
	QueryString     string `json:"query_string"`
	QueryDigestText string `json:"query_digest_text"`
	QueryDigestMd5  string `json:"query_digest_md5"`
	QueryCommand    string `json:"query_command"`
	QueryLength     int    `json:"query_length"`
	// QueryDbName parsed from query_string
	QueryDbName string `json:"query_db_name"`
	TableNames  string `json:"table_names"`
	// ThreadId        int    `json:"thread_id"`
}

func (m *MysqlSlowLogModel) TableName() string {
	return "tb_mysql_slow_log"
}

func (m *MysqlSlowLogModel) MigrateSchema(w base.DSWriter) error {
	slog.Info("run migrate for MysqlSlowLogModel", slog.String("table", m.TableName()))
	dbWriter, ok := w.(base.GormMigrator)
	if !ok {
		return errors.Errorf("writer_type=%s has no gorm db for custom migrate: %s", w.Type(), m.TableName())
	}
	db := dbWriter.GormDB()
	if w.Type() == "mysql" || w.Type() == "mysql_raw" {
		createTableSql := ""
		timeNow := time.Now()

		// 第一次 migrate 创建表的时候，同时创建未来 7 天的分区
		partitionsPreCreated := []string{}
		for i := -7; i < 7; i++ {
			days := cmutil.TimeToDays(timeNow.AddDate(0, 0, i))
			dateint := cast.ToInt(timeNow.AddDate(0, 0, i).Format("20060102"))
			partitionsPreCreated = append(partitionsPreCreated,
				fmt.Sprintf("PARTITION p%d VALUES LESS THAN (%d) ENGINE = InnoDB", dateint, days+1))
		}
		//partitionInfo = append(partitionInfo, "PARTITION pmax VALUES LESS THAN (MAXVALUE) ENGINE = InnoDB")
		partitionInfo := []string{
			"/*!50100 PARTITION BY RANGE (to_days(`dteventtimehour`))",
			"(",
			strings.Join(partitionsPreCreated, ",\n"),
			")",
			"*/",
		}
		createTableSql = CREATE_TABLE_SLOWLOG_MYSQL + strings.Join(partitionInfo, "\n")
		if err := db.Exec(fmt.Sprintf(createTableSql, m.TableName())).Error; err != nil {
			slog.Error("create table failed", slog.Any("err", err), slog.String("sql", createTableSql))
			return err
		}
		return nil
	} else if w.Type() == "doris" {
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
	} else if writer, ok := w.(*sinker.MysqlWriter); ok {
		return m.dorisCreate(objs, writer.GormDB())
	} else {
		//return errors.Errorf("not implement custom writer: %s", w.Type())
		// mysql writer?
		newObj := objs.([]MysqlSlowLogModel)
		return w.WriteBatch(m, newObj)
	}
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
  thedate int NOT NULL,
  log_time datetime NOT NULL,
  dteventtimestamp datetime NOT NULL,
  query_digest_md5 varchar(60) DEFAULT NULL,
  instance_host varchar(60) DEFAULT NULL,
  instance_port int DEFAULT NULL,
  shard_value int DEFAULT NULL,
  cluster_type varchar(60) DEFAULT NULL,

  query_time float DEFAULT NULL,
  lock_time float DEFAULT NULL,
  rows_examined int DEFAULT NULL,
  rows_sent int DEFAULT NULL,
  query_digest_text text DEFAULT NULL,
  query_string text DEFAULT NULL,
  query_length int DEFAULT NULL,
  query_command varchar(60) DEFAULT NULL,
  query_db_name varchar(127) DEFAULT NULL,
  table_names varchar(1024) DEFAULT NULL,
  db_name varchar(100) DEFAULT NULL,
  table_name varchar(100) DEFAULT NULL,
    
  bk_biz_id int DEFAULT NULL,
  bk_cloud_id int DEFAULT NULL,
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 
`

var CREATE_TABLE_SLOWLOG_DORIS = `
CREATE TABLE IF NOT EXISTS %s (
  cluster_domain varchar(255) NOT NULL,
  instance_role varchar(60) NULL,
  query_digest_md5 varchar(100) NULL,
  dteventtimehour datetime NOT NULL COMMENT "datetime precision to hour, used as where,group-by,expire",

  log_time datetime NOT NULL,
  dteventtimestamp datetime NOT NULL,
  thedate int NOT NULL,
  instance_host varchar(60) NULL,
  instance_port int NULL,

  query_time float NULL,
  lock_time float NULL,
  rows_examined int NULL,
  rows_sent int NULL,
    
  query_digest_text varchar(8192) NULL,
  query_string string NULL,
  query_length int NULL,
  query_command varchar(60) NULL,
  query_db_name varchar(100) NULL,
  db_name varchar(100) NULL,
  table_names varchar(1024) NULL,

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
	queryString, err := strconv.Unquote(string(data))
	if err != nil || queryString == "" {
		return fmt.Errorf("invalid data: %s", data)
	}
	logParsed, err := parseOneSlowLog(queryString, true)
	if err != nil {
		return errors.WithMessagef(err, "parse slow log failed: %s", queryString)
	}
	// sql解析结果字段
	_ = copier.Copy(m, logParsed)
	// 维度字段
	dimExt := &DimExt{}
	config := &mapstructure.DecoderConfig{
		Metadata: nil,
		Result:   dimExt,
		TagName:  "json", // Specify the custom tag name here
	}

	decoder, _ := mapstructure.NewDecoder(config)
	_ = decoder.Decode(msg.Ext)
	_ = copier.Copy(m, dimExt)
	m.BkBizId = cast.ToInt(dimExt.BkBizId)
	m.BkCloudId = cast.ToInt(dimExt.BkCloudId)
	m.InstancePort = cast.ToInt(dimExt.InstancePort)

	// 公共的字段
	m.SqlTimestamp = msg.Ts
	m.DtEventTimeStamp = msg.LogTime.Time
	m.LogTime = msg.UtcTime.Time

	m.TheDate, _ = strconv.Atoi(m.LogTime.Format("20060102"))
	m.DtEventTimeHour = m.LogTime.Format("2006-01-02 15")

	return nil
}
