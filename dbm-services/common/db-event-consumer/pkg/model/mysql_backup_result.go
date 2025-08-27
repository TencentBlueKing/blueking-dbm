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
	"log/slog"
	"time"

	"github.com/go-playground/validator/v10"
	sb "github.com/huandu/go-sqlbuilder"
	"github.com/jinzhu/copier"
	"github.com/pkg/errors"
	"gorm.io/gorm"

	"dbm-services/common/db-event-consumer/pkg/sinker"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
)

type MysqlBackupResultModel struct {
	BaseModel `json:",inline" gorm:"embedded" xorm:"extends"`
	// dbareport.ModelBackupReport

	BackupId        string `json:"backup_id" db:"backup_id" gorm:"column:backup_id;type:varchar(60);NOT NULL;index:uk_cluster,unique,priority:4" validate:"required"`
	BackupType      string `json:"backup_type" db:"backup_type" gorm:"column:backup_type;type:varchar(32);NOT NULL"`
	ClusterId       int    `json:"cluster_id" db:"cluster_id" gorm:"column:cluster_id;type:int;NOT NULL"`
	ClusterAddress  string `json:"cluster_address" db:"cluster_address" gorm:"column:cluster_address;type:varchar(255);NOT NULL;index:uk_cluster,unique,priority:1"`
	BackupHost      string `json:"backup_host" db:"backup_host" gorm:"column:backup_host;type:varchar(32);NOT NULL;index:uk_hostport,unique,priority:1"`
	BackupPort      int    `json:"backup_port" db:"backup_port" gorm:"column:backup_port;type:int;NOT NULL;index:uk_hostport,unique,priority:2"`
	MysqlRole       string `json:"mysql_role" db:"mysql_role" gorm:"column:mysql_role;type:varchar(32);NOT NULL;index:uk_hostport,unique,priority:3;;index:uk_cluster,unique,priority:3"`
	ShardValue      int    `json:"shard_value" db:"shard_value" gorm:"column:shard_value;type:int;NOT NULL;index:uk_cluster,unique,priority:2"`
	BillId          string `json:"bill_id" db:"bill_id" gorm:"column:bill_id;type:varchar(32);NOT NULL"`
	BkBizId         int    `json:"bk_biz_id" db:"bk_biz_id" gorm:"column:bk_biz_id;type:int;NOT NULL"`
	MysqlVersion    string `json:"mysql_version" db:"mysql_version" gorm:"column:mysql_version;type:varchar(120);NOT NULL"`
	DataSchemaGrant string `json:"data_schema_grant" db:"data_schema_grant" gorm:"column:data_schema_grant;type:varchar(32);NOT NULL"`
	// IsFullBackup 是否包含数据的全备
	IsFullBackup bool `json:"is_full_backup" db:"is_full_backup" gorm:"column:is_full_backup;type:tinyint;NOT NULL"`
	// IsStandby 是否是 standby, yes/no, empty means unknown
	IsStandby            string    `json:"is_standby" db:"is_standby" gorm:"column:is_standby;type:varchar(10);NOT NULL"`
	FileRetentionTag     string    `json:"file_retention_tag" db:"file_retention_tag" gorm:"column:file_retention_tag;type:varchar(32);NOT NULL"`
	TotalFilesize        uint64    `json:"total_filesize" db:"total_filesize" gorm:"column:total_filesize;type:bigint;NOT NULL"`
	BackupConsistentTime time.Time `json:"backup_consistent_time" db:"backup_consistent_time" gorm:"column:backup_consistent_time;type:TIMESTAMP;default:'1970-01-02 00:00:00';index:uk_hostport,unique,priority:4"`
	BackupBeginTime      time.Time `json:"backup_begin_time" db:"backup_begin_time" gorm:"column:backup_begin_time;type:TIMESTAMP NULL;default:null"`
	BackupEndTime        time.Time `json:"backup_end_time" db:"backup_end_time" gorm:"column:backup_end_time;type:TIMESTAMP NULL;default:null"`
	BackupMethod         string    `json:"backup_method" db:"backup_method" gorm:"column:backup_method;type:varchar(32)"`

	BinlogInfo   json.RawMessage `json:"binlog_info" db:"binlog_info" gorm:"column:binlog_info;type:text;NOT NULL"`
	FileList     json.RawMessage `json:"file_list" db:"file_list" gorm:"column:file_list;type:text;NOT NULL"`
	ExtraFields  json.RawMessage `json:"extra_fields" db:"extra_fields" gorm:"column:extra_fields;type:text;NOT NULL"`
	BackupStatus string          `json:"backup_status" db:"backup_status" gorm:"column:backup_status;type:varchar(32);NOT NULL"`
}

func (m *MysqlBackupResultModel) TableName() string {
	return "tb_mysql_backup_result"
}

func (m *MysqlBackupResultModel) MigrateSchema(w sinker.DSWriter) error {
	slog.Info("run migrate for MysqlBackupResultModel", slog.String("table", m.TableName()))
	if w.Type() == "mysql" {
		dbWriter := w.(*sinker.MysqlWriter)
		db := dbWriter.GormDB()
		if err := db.Migrator().AutoMigrate(&m); err != nil {
			return err
		}
		/*
			if err := AddIndex(db, m.TableName(), "uk_hostport",
				[]string{"backup_host", "backup_port", "mysql_role", "backup_consistent_time"}, true, true); err != nil {
				return err
			}
			if err := AddIndex(db, m.TableName(), "uk_cluster",
				[]string{"cluster_address", "shard_value", "mysql_role", "backup_id"}, true, true); err != nil {
				return err
			}
		*/
		if err := CreateOrUpdateIndex(db, m.TableName(), "idx_backuptime",
			[]string{"backup_consistent_time"}, false, true); err != nil {
			return err
		}
		if err := CreateOrUpdateIndex(db, m.TableName(), "idx_backupid",
			[]string{"backup_id"}, false, true); err != nil {
			return err
		}
		if err := CreateOrUpdateIndex(db, m.TableName(), "idx_clusterid",
			[]string{"cluster_id"}, false, true); err != nil {
			return err
		}
		return nil
	} else if w.Type() == "mysql_xorm" {
		return w.AutoMigrate(m)
	} else {
		return w.AutoMigrate(m)
	}
}

func (m *MysqlBackupResultModel) Create(objs interface{}, w sinker.DSWriter) error {
	if w.Type() == "mysql" {
		if writer, ok := w.(*sinker.MysqlWriter); ok {
			return m.mysqlCreate(objs, writer.GormDB())
		} else if writer, ok := w.(*sinker.XormWriter); ok {
			return errors.Errorf("not implement custom writer: %s", writer.Type())
		} else {
			return errors.Errorf("not implement custom writer: %s", w.Type())
		}
	} else {
		newObj := objs.([]MysqlBackupResultModel)
		return w.WriteBatch(m, newObj)
	}
}

func (m *MysqlBackupResultModel) mysqlCreate(i interface{}, db *gorm.DB) error {
	kafkaObjs, ok := i.([]MysqlBackupResultModel)
	if !ok {
		kafkaObjs = []MysqlBackupResultModel{i.(MysqlBackupResultModel)}
	}

	builder := sb.NewInsertBuilder()
	builder.ReplaceInto(m.TableName())
	builder.Cols("cluster_address",
		"backup_host",
		"backup_port",
		"mysql_role",
		"shard_value",
		"backup_id",
		"backup_type",
		"data_schema_grant",
		"is_full_backup",
		"is_standby",
		"backup_consistent_time",
		"backup_begin_time",
		"backup_end_time",
		"backup_status",
		"backup_method",
		"mysql_version",
		"file_retention_tag",
		"total_filesize",
		"cluster_id",
		"bk_biz_id",
		"bill_id",
		"binlog_info",
		"extra_fields",
		"file_list",
		"event_report_timestamp",
	)

	for _, kafkaObj := range kafkaObjs {
		var modelObj = &MysqlBackupResultModel{}
		if err := copier.Copy(modelObj, kafkaObj); err != nil {
			return err
		}
		modelObj.FileList, _ = json.Marshal(kafkaObj.FileList)
		modelObj.BinlogInfo, _ = json.Marshal(kafkaObj.BinlogInfo)
		modelObj.ExtraFields, _ = json.Marshal(kafkaObj.ExtraFields)
		modelObj.BkBizId = kafkaObj.BkBizId
		builder.Values(
			modelObj.ClusterAddress,
			modelObj.BackupHost,
			modelObj.BackupPort,
			modelObj.MysqlRole,
			modelObj.ShardValue,
			modelObj.BackupId,
			modelObj.BackupType,
			modelObj.DataSchemaGrant,
			modelObj.IsFullBackup,
			modelObj.IsStandby,
			modelObj.BackupConsistentTime.UTC(), // 因为这里没有用 gorm 来来写入，所以需要手动转换时区(conn用的是 utc)
			modelObj.BackupBeginTime.UTC(),
			modelObj.BackupEndTime.UTC(),
			modelObj.BackupStatus,
			modelObj.BackupMethod,
			modelObj.MysqlVersion,
			modelObj.FileRetentionTag,
			modelObj.TotalFilesize,
			modelObj.ClusterId,
			modelObj.BkBizId,
			modelObj.BillId,
			modelObj.BinlogInfo,
			modelObj.ExtraFields,
			modelObj.FileList,
			modelObj.EventReportTimestamp,
		)
	}

	sqlStr, sqlArgs := builder.Build()
	sqlFull, err := sb.MySQL.Interpolate(sqlStr, sqlArgs)
	if err != nil {
		return err
	}
	err = db.Model(m).Exec(sqlFull).Error
	if err != nil {
		slog.Error("replace message",
			slog.Any("msg", err), slog.String("sql", sqlStr), slog.Any("args", sqlArgs))
		//return err
	}
	return nil
}

func (m *MysqlBackupResultModel) Validate() error {
	validate := validator.New()
	return validate.Struct(m)
	//validationErrors := err.(validator.ValidationErrors)
}

func (m *MysqlBackupResultModel) UnmarshalJSON(data []byte) error {
	msg := MysqlBackupResultMsg{}
	if err := json.Unmarshal(data, &msg); err != nil {
		return err
	}
	if err := copier.Copy(&m, msg); err != nil {
		return err
	}

	m.FileList, _ = json.Marshal(msg.FileList)
	m.BinlogInfo, _ = json.Marshal(msg.BinlogInfo)
	m.ExtraFields, _ = json.Marshal(msg.ExtraFields)
	m.BkBizId = msg.BkBizId
	return nil
}

type MysqlBackupResultMsg struct {
	BaseModel `json:",inline"`
	//dbareport.IndexContent `json:",inline"`
	dbareport.BackupMetaFileBase `json:",inline"`
	dbareport.ExtraFields        `json:",inline"`
	BinlogInfo                   dbareport.BinlogStatusInfo `json:"binlog_info" db:"binlog_info"`
	FileList                     []*dbareport.TarFileItem   `json:"file_list" db:"file_list"`
}
