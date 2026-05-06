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

type MysqlTableSize struct {
	ID uint `gorm:"primaryKey;autoIncrement:true"`
	// TheDate 20250101
	TheDate int `gorm:"column:thedate;type:int;not null" json:"thedate" db:"thedate"`
	// DtEventTimeStamp 1577836800000
	DtEventTimeStamp int64 `gorm:"column:dteventtimestamp;type:bigint;not null" json:"dteventtimestamp" db:"dteventtimestamp"`
	// DtEventTimeHour	'2020-01-01 01:00:00'
	DtEventTimeHour string `gorm:"column:dteventtimehour;type:varchar(127);not null" json:"dteventtimehour" db:"dteventtimehour"`
	// ReportTime	'2020-01-01 01:02:03'
	ReportTime       time.Time `gorm:"column:report_time;type:varchar(127);not null" json:"report_time" db:"report_time"`
	BkCloudId        int       `gorm:"column:bk_cloud_id;type:int;not null" json:"bk_cloud_id" db:"bk_cloud_id"`
	BkBizId          int       `gorm:"column:bk_biz_id;type:int;not null" json:"bk_biz_id" db:"bk_biz_id"`
	ClusterDomain    string    `gorm:"column:cluster_domain;type:varchar(127);not null" json:"cluster_domain" db:"cluster_domain"`
	InstanceHost     string    `gorm:"column:instance_host;type:varchar(127);not null" json:"instance_host" db:"instance_host"`
	InstancePort     int       `gorm:"column:instance_port;type:int;not null" json:"instance_port" db:"instance_port"`
	InstanceRole     string    `gorm:"column:instance_role;type:varchar(127);not null" json:"instance_role" db:"instance_role"`
	MachineType      string    `gorm:"column:machine_type;type:varchar(127);not null" json:"machine_type" db:"machine_type"`
	OriginalDatabase string    `gorm:"column:original_database_name;type:varchar(127);not null" json:"original_database_name" db:"original_database_name"`
	Database         string    `gorm:"column:database_name;type:varchar(127);not null" json:"database_name" db:"database_name"`
	Table            string    `gorm:"column:table_name;type:varchar(127);not null" json:"table_name" db:"table_name"`
	DatabaseSize     int64     `gorm:"column:database_size;type:bigint;not null" json:"database_size" db:"database_size"`
	TableSize        int64     `gorm:"column:table_size;type:bigint;not null" json:"table_size" db:"table_size"`
}

func (m *MysqlTableSize) TableName() string {
	return "mysql_db_table_size"
}

func (m *MysqlTableSize) MigrateSchema(w base.DSWriter) error {
	slog.Info("run migrate for MysqlTableSize", slog.String("table", m.TableName()))
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
		createTableSql = CREATE_TABLE_SQL_MYSQL + strings.Join(partitionInfo, "\n")
		if err := db.Exec(fmt.Sprintf(createTableSql, m.TableName())).Error; err != nil {
			slog.Error("create table failed", slog.Any("err", err), slog.String("sql", createTableSql))
			return err
		}
		return nil
	} else if w.Type() == "doris" {
		if err := db.Exec(fmt.Sprintf(CREATE_TABLE_SQL_DORIS, m.TableName())).Error; err != nil {
			slog.Error("create table failed", slog.Any("err", err), slog.String("sql", CREATE_TABLE_SQL_DORIS))
			return err
		}
		return nil
	} else {
		return w.AutoMigrate(m)
	}
}

func (m *MysqlTableSize) StrictSchema() bool {
	return true
}

func (m *MysqlTableSize) Create(objs interface{}, w base.DSWriter) error {
	if writer, ok := w.(*sinker.DorisWriter); ok {
		return m.dorisCreate(objs, writer.GormDB())
	} else if writer, ok := w.(*sinker.MysqlWriter); ok {
		return m.dorisCreate(objs, writer.GormDB())
	} else {
		//return errors.Errorf("not implement custom writer: %s", w.Type())
		// mysql writer?
		newObj := objs.([]MysqlTableSize)
		return w.WriteBatch(m, newObj)
	}
}

func (m *MysqlTableSize) dorisCreate(i interface{}, db *gorm.DB) error {
	// 从 kafka msg 里面反序列化出来，可能是单个，也可能是批量
	// custom writer 反序列化出来，一半是具体的对象，不是 map (比较难处理)
	kafkaObjs, ok := i.([]MysqlTableSize)
	if !ok {
		kafkaObjs = []MysqlTableSize{i.(MysqlTableSize)}
	}

	builder := sb.NewInsertBuilder()
	builder.InsertInto(m.TableName())
	builder.Cols(
		"thedate", "dteventtimestamp", "dteventtimehour",
		"report_time",
		"bk_biz_id",
		"cluster_domain",
		"instance_host",
		"instance_port",
		"original_database_name",
		"database_name",
		"table_name",
		"table_size",
		"database_size",
		"machine_type",
		"instance_role",
		"bk_cloud_id",
	)

	for _, kafkaObj := range kafkaObjs {
		kafkaObj.TheDate, _ = strconv.Atoi(kafkaObj.ReportTime.Format("20060102"))
		kafkaObj.DtEventTimeStamp = kafkaObj.ReportTime.UnixMilli()
		kafkaObj.DtEventTimeHour = kafkaObj.ReportTime.Format("2006-01-02 15")
		// slog.Debug("unmarshal task obj", slog.Any("obj", kafkaObj))
		builder.Values(
			kafkaObj.TheDate, kafkaObj.DtEventTimeStamp, kafkaObj.DtEventTimeHour,
			kafkaObj.ReportTime,
			kafkaObj.BkBizId,
			kafkaObj.ClusterDomain,
			kafkaObj.InstanceHost,
			kafkaObj.InstancePort,
			kafkaObj.OriginalDatabase,
			kafkaObj.Database,
			kafkaObj.Table,
			kafkaObj.TableSize,
			kafkaObj.DatabaseSize,
			kafkaObj.MachineType,
			kafkaObj.InstanceRole,
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

var CREATE_TABLE_SQL_MYSQL = `
CREATE TABLE IF NOT EXISTS %s (
  id bigint NOT NULL AUTO_INCREMENT,
  cluster_domain varchar(200) NOT NULL,
  dteventtimehour datetime NOT NULL COMMENT 'datetime precision to hour, used as where,group-by,expire',
  report_time varchar(32) DEFAULT NULL,
  thedate int NOT NULL,
  dteventtimestamp bigint NOT NULL,
  instance_host varchar(60) DEFAULT NULL,
  instance_port int DEFAULT NULL,
  shard_value int DEFAULT NULL,
  database_name varchar(100) DEFAULT NULL,
  table_name varchar(100) DEFAULT NULL,
  table_size bigint DEFAULT NULL,
  original_database_name varchar(100) DEFAULT NULL,
  database_size bigint DEFAULT NULL,
  machine_type varchar(60) DEFAULT NULL,
  instance_role varchar(60) DEFAULT NULL,
  bk_biz_id int DEFAULT NULL,
  bk_cloud_id int DEFAULT NULL,
  PRIMARY KEY (cluster_domain,dteventtimehour,id),
  KEY idx_0 (id),
  KEY idx_1 (cluster_domain,database_name,original_database_name,table_name,dteventtimehour),
  KEY idx_2 (cluster_domain,dteventtimehour),
  KEY idx_3 (dteventtimehour,cluster_domain,database_name),
  KEY idx_4 (dteventtimehour),
  KEY idx_5 (instance_host,instance_port)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 

`

var CREATE_TABLE_SQL_DORIS = `
CREATE TABLE IF NOT EXISTS %s (
  cluster_domain varchar(200) NOT NULL,
  dteventtimehour datetime NOT NULL COMMENT "datetime precision to hour, used as where,group-by,expire",
  report_time varchar(32) NULL,
  thedate int NOT NULL,
  dteventtimestamp bigint NOT NULL,
  instance_host varchar(60) NULL,
  instance_port int NULL,
  shard_value int NULL,
  database_name varchar(100) NULL,
  table_name varchar(100) NULL,
  table_size bigint NULL,
  original_database_name varchar(100) NULL,
  database_size bigint NULL,
  machine_type varchar(60) NULL,
  instance_role varchar(60) NULL,
  bk_biz_id int NULL,
  bk_cloud_id int NULL
) ENGINE=OLAP
DUPLICATE KEY(cluster_domain, dteventtimehour)
PARTITION BY RANGE(dteventtimehour)()
DISTRIBUTED BY HASH(cluster_domain) BUCKETS 12
PROPERTIES (
  "replication_allocation" = "tag.location.default: 1",
  "min_load_replica_num" = "-1",
  "bloom_filter_columns" = "cluster_domain, database_name, bk_biz_id, table_name",
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
