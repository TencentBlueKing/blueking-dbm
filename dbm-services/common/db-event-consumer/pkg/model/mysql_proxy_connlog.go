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
	"regexp"
	"strconv"
	"strings"
	"time"

	sb "github.com/huandu/go-sqlbuilder"
	"github.com/pkg/errors"
	"github.com/spf13/cast"
	"gorm.io/gorm"

	"dbm-services/common/db-event-consumer/pkg/base"
	"dbm-services/common/db-event-consumer/pkg/sinker"
	"dbm-services/common/go-pubpkg/cmutil"
)

type MysqlProxyConnlog struct {
	ID uint `gorm:"primaryKey;autoIncrement:true"`
	// TheDate 20250101
	TheDate int `gorm:"column:thedate;type:int;not null" json:"thedate" db:"thedate"`
	// DtEventTimeStamp 1577836800000
	DtEventTimeStamp time.Time `gorm:"column:dteventtimestamp;type:bigint;not null" json:"dtEventTimeStamp" db:"dteventtimestamp"`
	// DtEventTimeHour	'2020-01-01 01:00:00'
	DtEventTimeHour string `gorm:"column:dteventtimehour;type:varchar(127);not null" json:"dteventtimehour" db:"dteventtimehour"`
	BkBizId         int    `gorm:"column:bk_biz_id;type:int;not null" json:"bk_biz_id" db:"bk_biz_id"`
	BkCloudId       int    `gorm:"column:bk_cloud_id;type:int;not null" json:"bk_cloud_id" db:"bk_cloud_id"`
	ClusterDomain   string `gorm:"column:cluster_domain;type:varchar(127);not null" json:"__module__" db:"cluster_domain"`
	//ClusterDomain   string `gorm:"column:cluster_domain;type:varchar(127);not null" json:"cluster_domain" db:"cluster_domain"`
	//BkCloudId       int    `gorm:"column:bk_cloud_id;type:int;not null" json:"cloudId" db:"bk_cloud_id"`
	// ProxyIp proxy serverIp
	ProxyIp string `gorm:"column:proxy_ip;type:varchar(127);not null" json:"proxy_ip" db:"proxy_ip"`
	// ProxyPort mysql-proxy port
	ProxyPort int `gorm:"column:proxy_port;type:int;not null" json:"proxy_port" db:"proxy_port"`

	ClientIp  string    `gorm:"column:client_ip;type:varchar(127);not null" json:"client_ip" db:"client_ip"`
	ConnUser  string    `gorm:"column:conn_user;type:varchar(127);not null" json:"conn_user" db:"conn_user"`
	ConnTime  time.Time `gorm:"column:conn_time;type:datetime;not null" json:"conn_time" db:"conn_time"`
	SessionId int64     `gorm:"column:session_id;type:bigint;not null" json:"session_id" db:"session_id"`
}

func (m *MysqlProxyConnlog) TableName() string {
	return "mysql_proxy_connlog"
}

// UnmarshalItem 实现 BklogUnmarshalItem 接口
// item.Data 格式: 2026-08-10 19:43:31: (critical) conn_log, current user is 'user1'@'1.2.3.4' 13872793
// 解析出 conn_time, conn_user, client_ip, session_id
func (m *MysqlProxyConnlog) UnmarshalItem(data []byte, msg base.MessageWrapper) error {
	queryString, err := strconv.Unquote(string(data))
	if err != nil || queryString == "" {
		return fmt.Errorf("invalid data: %s", data)
	}

	// 解析正则: 2026-08-10 19:43:31: (critical) conn_log, current user is 'user'@'ip' session_id
	re := connlogRegexp
	matches := re.FindStringSubmatch(queryString)
	if matches == nil {
		return fmt.Errorf("connlog format not match(%s): %s ", msg.Ip, queryString)
	}
	// matches[1]=datetime, matches[2]=user, matches[3]=ip, matches[4]=session_id
	connTime, err := time.ParseInLocation("2006-01-02 15:04:05", matches[1], time.Local)
	if err != nil {
		return errors.WithMessagef(err, "parse conn_time failed: %s", matches[1])
	}
	//m.ClusterDomain = msg.BkModule
	m.BkCloudId = msg.BkCloudId
	m.DtEventTimeStamp = connTime
	m.ProxyIp = msg.Ip

	m.ConnTime = connTime
	m.ConnUser = matches[2]
	m.ClientIp = matches[3]
	m.SessionId, _ = strconv.ParseInt(matches[4], 10, 64)

	// 公共时间字段
	m.TheDate, _ = strconv.Atoi(connTime.Format("20060102"))
	m.DtEventTimeHour = connTime.Format("2006-01-02 15")

	// 维度字段从 msg.Ext 中提取
	if msg.Ext != nil {
		m.BkBizId = cast.ToInt(msg.Ext["app_id"])
		m.BkCloudId = cast.ToInt(msg.Ext["bk_cloud_id"])
		m.ClusterDomain = cast.ToString(msg.Ext["cluster_domain"])
	}
	return nil
}

// connlogRegexp 解析 proxy connlog 格式的正则
// 格式: 2026-08-10 19:43:31: (critical) conn_log, current user is 'user'@'ip' session_id
var connlogRegexp = regexp.MustCompile(`^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}):\s*\(\w+\)\s*conn_log,\s*current user is '([^']*)'@'([^']*)'\s+(-?\d+)$`)

func (m *MysqlProxyConnlog) MigrateSchema(w base.DSWriter) error {
	slog.Info("run migrate for MysqlProxyConnlog", slog.String("table", m.TableName()))
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
		createTableSql = CREATE_TABLE_MYSQL_MYSQL_PROXY_CONNLOG + strings.Join(partitionInfo, "\n")
		if err := db.Exec(fmt.Sprintf(createTableSql, m.TableName())).Error; err != nil {
			slog.Error("create table failed", slog.Any("err", err), slog.String("sql", createTableSql))
			return err
		}
		return nil
	} else if w.Type() == "doris" {
		if err := db.Exec(fmt.Sprintf(CREATE_TABLE_DORIS_MYSQL_PROXY_CONNLOG, m.TableName())).Error; err != nil {
			slog.Error("create table failed", slog.Any("err", err), slog.String("sql", CREATE_TABLE_SQL_DORIS))
			return err
		}
		return nil
	} else {
		return w.AutoMigrate(m)
	}
}

func (m *MysqlProxyConnlog) StrictSchema() bool {
	return true
}

func (m *MysqlProxyConnlog) Create(objs interface{}, w base.DSWriter) error {
	if writer, ok := w.(*sinker.DorisWriter); ok {
		return m.dorisCreate(objs, writer.GormDB())
	} else if writer, ok := w.(*sinker.MysqlWriter); ok {
		return m.dorisCreate(objs, writer.GormDB())
	} else {
		//return errors.Errorf("not implement custom writer: %s", w.Type())
		// mysql writer?
		newObj := objs.([]MysqlProxyConnlog)
		return w.WriteBatch(m, newObj)
	}
}

func (m *MysqlProxyConnlog) dorisCreate(i interface{}, db *gorm.DB) error {
	// 从 kafka msg 里面反序列化出来，可能是单个，也可能是批量
	// custom writer 反序列化出来，一半是具体的对象，不是 map (比较难处理)
	kafkaObjs, ok := i.([]MysqlProxyConnlog)
	if !ok {
		kafkaObjs = []MysqlProxyConnlog{i.(MysqlProxyConnlog)}
	}

	builder := sb.NewInsertBuilder()
	builder.InsertInto(m.TableName())
	builder.Cols(
		"thedate", "dteventtimestamp", "dteventtimehour",
		"cluster_domain",
		"proxy_ip",
		"conn_time",
		"client_ip",
		"conn_user",
		"session_id",
		"bk_biz_id",
		"bk_cloud_id",
	)
	for _, kafkaObj := range kafkaObjs {
		kafkaObj.TheDate, _ = strconv.Atoi(kafkaObj.DtEventTimeStamp.Format("20060102"))
		kafkaObj.DtEventTimeHour = kafkaObj.DtEventTimeStamp.Format("2006-01-02 15")
		// slog.Debug("unmarshal task obj", slog.Any("obj", kafkaObj))
		builder.Values(
			kafkaObj.TheDate, kafkaObj.DtEventTimeStamp, kafkaObj.DtEventTimeHour,
			kafkaObj.ClusterDomain,
			kafkaObj.ProxyIp,
			kafkaObj.ConnTime,
			kafkaObj.ClientIp,
			kafkaObj.ConnUser,
			kafkaObj.SessionId,
			kafkaObj.BkBizId,
			kafkaObj.BkCloudId,
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
			slog.Any("msg", err), slog.String("sql", sqlStr), slog.Any("args", sqlArgs))
		//return err
	}
	return nil
}

var CREATE_TABLE_MYSQL_MYSQL_PROXY_CONNLOG = `
`

var CREATE_TABLE_DORIS_MYSQL_PROXY_CONNLOG = `
CREATE TABLE IF NOT EXISTS %s (
  cluster_domain varchar(200) NOT NULL,
  dteventtimehour datetime NOT NULL COMMENT "datetime precision to hour, used as where,group-by,expire",
  thedate int NOT NULL,
  dteventtimestamp datetime NOT NULL,
  proxy_ip varchar(60) NOT NULL,
  conn_time datetime NOT NULL,
  client_ip varchar(60) NULL,
  conn_user varchar(100) NULL,
  session_id int NULL,
  bk_biz_id int NULL,
  bk_cloud_id int NULL
) ENGINE=OLAP
DUPLICATE KEY(cluster_domain, dteventtimehour)
PARTITION BY RANGE(dteventtimehour)()
DISTRIBUTED BY HASH(cluster_domain) BUCKETS 12
PROPERTIES (
  "replication_allocation" = "tag.location.default: 1",
  "min_load_replica_num" = "-1",
  "bloom_filter_columns" = "cluster_domain, instance_host, conn_user",
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
